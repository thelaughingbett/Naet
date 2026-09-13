# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin
from .positions import COUNCIL_POSITION_CHOICES, CouncilPosition


class Election(BaseModelMixin):
    """
    A single election cycle — usually electing an entire CouncilTerm's
    seats at once, but also usable for a one-off by-election.
    """

    STATUS_CHOICES = [
        ("upcoming",    "Upcoming"),
        ("nominations", "Nominations Open"),
        ("campaigning", "Campaign Period"),
        ("voting",      "Voting Open"),
        ("tallying",    "Tallying / Results Pending"),
        ("completed",   "Completed"),
        ("cancelled",   "Cancelled"),
    ]

    term = models.ForeignKey(
        "CouncilTerm",
        on_delete=models.CASCADE,
        related_name="elections",
        help_text="The council term these seats are being elected into.",
    )

    title = models.CharField(
        max_length=200,
        help_text="e.g. 'General Elections 2026/2027', 'Treasurer By-Election'.",
    )

    nomination_start = models.DateTimeField()
    nomination_end = models.DateTimeField()
    voting_start = models.DateTimeField()
    voting_end = models.DateTimeField()

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="upcoming",
        db_index=True,
    )

    returning_officer = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="elections_overseen",
        limit_choices_to={"is_staff": True},
        help_text="Electoral Board / Dean of Students' office representative overseeing this election.",
    )

    class Meta:
        ordering = ["-voting_start"]
        verbose_name = "Council Election"
        verbose_name_plural = "Council Elections"

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    @property
    def is_voting_open(self):
        now = timezone.now()
        return self.status == "voting" and self.voting_start <= now <= self.voting_end

    def clean(self):
        super().clean()

        ordered_pairs = [
            (self.nomination_start, self.nomination_end, "nomination_end"),
            (self.nomination_end, self.voting_start, "voting_start"),
            (self.voting_start, self.voting_end, "voting_end"),
        ]
        for earlier, later, field_name in ordered_pairs:
            if earlier and later and later <= earlier:
                raise ValidationError({
                    field_name: "Each election stage must start after the previous one ends."
                })

    def declare_winners(self, installed_by=None):
        """
        Tally votes for every ElectionPosition under this election and
        install the top `seats_available` approved candidates as active
        CouncilPosition holders for `self.term`. Any existing active
        holder of a position being filled is vacated first. Intended to
        run once, after voting has closed.

        NOTE: ties for the last available seat aren't handled specially —
        `.order_by("-vote_count")[:seats_available]` on a tie picks
        whichever row the database happens to return first, which is not
        guaranteed to be deterministic across runs. Worth a tie-breaking
        rule (or at minimum a loud warning to the returning officer)
        before this is relied on for a real close result.
        """
        if self.status not in ("voting", "tallying"):
            raise ValidationError(
                "Winners can only be declared once voting has closed."
            )

        installed = []
        for election_position in self.positions.all():
            ranked = (
                election_position.candidates
                .filter(status="approved")
                .annotate(vote_count=models.Count("votes"))
                .order_by("-vote_count")
            )
            winners = list(ranked[:election_position.seats_available])

            if election_position.position == "school_rep":
                existing = CouncilPosition.objects.filter(
                    term=self.term,
                    position="school_rep",
                    school=election_position.school,
                    is_active=True,
                )
            else:
                existing = CouncilPosition.objects.filter(
                    term=self.term,
                    position=election_position.position,
                    is_active=True,
                )
            for holder in existing:
                holder.vacate(reason="Superseded by election results")

            for candidate in winners:
                position = CouncilPosition.objects.create(
                    term=self.term,
                    student=candidate.student,
                    position=election_position.position,
                    school=election_position.school,
                    source="elected",
                )
                installed.append(position)

        self.status = "completed"
        self.save()
        return installed


class ElectionPosition(BaseModelMixin):
    """A single seat (or set of seats) being contested within an Election."""

    election = models.ForeignKey(
        "Election",
        on_delete=models.CASCADE,
        related_name="positions",
    )

    position = models.CharField(
        max_length=30,
        choices=COUNCIL_POSITION_CHOICES,
    )

    # Only meaningful when position == 'school_rep'.
    school = models.ForeignKey(
        "School",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contested_council_seats",
    )

    seats_available = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("election", "position", "school")
        verbose_name = "Election Position"
        verbose_name_plural = "Election Positions"

    def __str__(self):
        label = self.get_position_display()
        if self.position == "school_rep" and self.school:
            label = f"{label} ({self.school.school_name})"
        return f"{self.election.title} — {label}"

    def clean(self):
        super().clean()

        if self.position == "school_rep" and not self.school_id:
            raise ValidationError({
                "school": "A school representative seat must specify which School it represents."
            })

        if self.position != "school_rep" and self.school_id:
            raise ValidationError({
                "school": "Only a School Representative seat should have a School set."
            })


class Candidate(BaseModelMixin):
    """A student's nomination for a specific ElectionPosition."""

    STATUS_CHOICES = [
        ("pending",       "Pending Vetting"),
        ("approved",      "Approved / Cleared to Run"),
        ("disqualified",  "Disqualified"),
        ("withdrawn",     "Withdrawn"),
    ]

    election_position = models.ForeignKey(
        "ElectionPosition",
        on_delete=models.CASCADE,
        related_name="candidates",
    )

    student = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="candidacies",
    )

    manifesto = models.TextField(
        blank=True,
        default=""
    )

    photo = models.ImageField(
        upload_to="candidate_photos/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    nominated_at = models.DateTimeField(default=timezone.now)

    vetted_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidates_vetted",
        limit_choices_to={"is_staff": True},
    )

    disqualification_reason = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ("election_position", "student")
        verbose_name = "Election Candidate"
        verbose_name_plural = "Election Candidates"

    def __str__(self):
        return f"{self.student} — {self.election_position} [{self.get_status_display()}]"

    @property
    def vote_count(self):
        return self.votes.count()

    def clean(self):
        super().clean()

        if self.status == "disqualified" and not self.disqualification_reason:
            raise ValidationError({
                "disqualification_reason": "A reason is required when disqualifying a candidate."
            })

        if self.election_position_id and self.nominated_at:
            election = self.election_position.election
            if not (election.nomination_start <= self.nominated_at <= election.nomination_end):
                raise ValidationError({
                    "nominated_at": "Nominations can only be submitted within the election's "
                                    "nomination window."
                })


class Vote(BaseModelMixin):
    """
    A single ballot cast by a student for one ElectionPosition.
    `candidate` is left null to represent an explicit abstention, so
    turnout can be measured separately from support for any one candidate.
    """

    election_position = models.ForeignKey(
        "ElectionPosition",
        on_delete=models.CASCADE,
        related_name="votes",
    )

    candidate = models.ForeignKey(
        "Candidate",
        on_delete=models.CASCADE,
        related_name="votes",
        null=True,
        blank=True,
    )

    voter = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="council_votes_cast",
    )

    cast_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One ballot per student per contested position — the actual
        # anti-double-voting guarantee.
        unique_together = ("election_position", "voter")
        verbose_name = "Council Vote"
        verbose_name_plural = "Council Votes"

    def __str__(self):
        choice = self.candidate.student if self.candidate else "Abstain"
        return f"{self.voter} → {self.election_position} : {choice}"

    def clean(self):
        super().clean()

        if self.election_position_id:
            election = self.election_position.election
            if not election.is_voting_open:
                raise ValidationError(
                    "Voting is not currently open for this election."
                )

        if self.candidate_id:
            if self.candidate.election_position_id != self.election_position_id:
                raise ValidationError({
                    "candidate": "This candidate is not contesting the selected position."
                })
            if self.candidate.status != "approved":
                raise ValidationError({
                    "candidate": "You can only vote for an approved candidate."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
