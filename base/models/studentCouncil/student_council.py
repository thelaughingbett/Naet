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


# ─────────────────────────────────────────────────────────────────────────────
# Shared position vocabulary
# ─────────────────────────────────────────────────────────────────────────────
# Used by both CouncilPosition (who currently holds the seat) and
# ElectionPosition (what's being contested) so the two stay in lockstep.
# TODO : This should be a model  and should have a permissions table for each role to help with template rendering
COUNCIL_POSITION_CHOICES = [
    ("chairperson",        "Chairperson / President"),
    ("deputy_chairperson", "Deputy Chairperson / Vice President"),
    ("secretary_general",  "Secretary General"),
    ("deputy_secretary",   "Deputy Secretary General"),
    ("treasurer",          "Treasurer"),
    ("academic_affairs_sec", "Academic Affairs Secretary"),
    ("welfare_sec",        "Welfare Secretary"),
    ("sports_sec",         "Sports and Games Secretary"),
    ("entertainment_sec",  "Entertainment Secretary"),
    ("ict_sec",            "ICT Secretary"),
    ("gender_affairs_sec", "Gender Affairs Secretary"),
    ("school_rep",         "School Representative"),
]

# Positions with campus-wide (not school-scoped) authority — used to keep
# grievance/proposal "assign to" pickers from offering school reps for
# things outside their remit, and elsewhere as a sanity check.
EXECUTIVE_POSITIONS = {
    "chairperson",
    "deputy_chairperson",
    "secretary_general",
    "deputy_secretary",
    "treasurer",
}


class CouncilTerm(BaseModelMixin):
    """
    A single Student Council's term of office. Spans a full academic year
    (potentially multiple Sessions), so it's tracked independently of
    Session rather than FK'd to one.
    """

    academic_year = models.CharField(
        max_length=9,
        unique=True,
        help_text="e.g. '2026/2027' — matches Session.academic_year format.",
    )

    theme = models.CharField(
        max_length=255,
        blank=True,
        default="Headless Chicken",
        help_text="This council's manifesto theme/slogan, if any.",
    )

    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True
    )

    is_current = models.BooleanField(default=False)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            # Only one council term can be "current" at a time.
            models.UniqueConstraint(
                fields=["is_current"],
                condition=models.Q(is_current=True),
                name="unique_current_council_term",
            )
        ]
        ordering = ["-start_date"]
        verbose_name = "Student Council Term"
        verbose_name_plural = "Student Council Terms"

    def __str__(self):
        return f"Student Council {self.academic_year}"

    @classmethod
    def current(cls):
        return cls.objects.filter(is_current=True).first()

    @property
    def executive(self):
        """The five principal officers, if filled — chair, deputy, sec-gen,
        deputy sec-gen, treasurer."""
        return self.positions.filter(
            is_active=True, position__in=EXECUTIVE_POSITIONS
        ).select_related("student__user")

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "End date cannot be earlier than the start date."
            })


class CouncilPosition(BaseModelMixin):
    """
    A student currently (or formerly) holding a council seat for a given
    term. Unlike club membership, there's no separate "rank and file"
    membership table — every council seat is a named position. Election
    outcomes are installed here via Election.declare_winners().
    """

    SOURCE_CHOICES = [
        ("elected",  "Elected"),
        ("appointed", "Appointed"),
        ("co_opted", "Co-opted"),
    ]

    term = models.ForeignKey(
        "CouncilTerm",
        on_delete=models.CASCADE,
        related_name="positions",
    )

    student = models.ForeignKey(
        "Student",
        on_delete=models.PROTECT,
        related_name="council_positions",
    )

    position = models.CharField(
        max_length=30,
        choices=COUNCIL_POSITION_CHOICES,
    )  # TODO :  make a foreign key relation to the council position choices model when created

    # Only meaningful (and required) when position == 'school_rep'.
    school = models.ForeignKey(
        "School",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="council_representatives",
    )

    source = models.CharField(
        max_length=15,
        choices=SOURCE_CHOICES,
        default="elected",
    )

    installed_at = models.DateField(default=timezone.now)
    vacated_at = models.DateField(
        null=True,
        blank=True
    )

    vacated_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="e.g. resignation, impeachment, graduation, disqualification.",
    )

    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            # One active holder per non-school-rep position per term.
            models.UniqueConstraint(
                fields=["term", "position"],
                condition=models.Q(is_active=True) & ~models.Q(
                    position="school_rep"),
                name="unique_active_council_position",
            ),
            # One active representative per school per term.
            models.UniqueConstraint(
                fields=["term", "school"],
                condition=models.Q(is_active=True, position="school_rep"),
                name="unique_active_school_rep_seat",
            ),
        ]
        ordering = ["term", "position"]
        verbose_name = "Council Position"
        verbose_name_plural = "Council Positions"

    def __str__(self):
        label = self.get_position_display()
        if self.position == "school_rep" and self.school:
            label = f"{label} ({self.school.school_name})"
        return f"{label} — {self.student} [{self.term.academic_year}]"

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

        if self.vacated_at and self.installed_at and self.vacated_at < self.installed_at:
            raise ValidationError({
                "vacated_at": "Vacate date cannot be earlier than the installation date."
            })

        if self.vacated_at and self.is_active:
            raise ValidationError({
                "is_active": "A position with a vacate date should not remain marked active."
            })

    def vacate(self, reason=""):
        self.is_active = False
        self.vacated_at = timezone.now().date()
        self.vacated_reason = reason
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
# Elections
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Proposals & Initiatives
# ─────────────────────────────────────────────────────────────────────────────

class CouncilProposal(BaseModelMixin):
    """
    A policy proposal or initiative raised for the council's consideration.
    Any student can submit one; a sitting council member can optionally
    sponsor/champion it before it's formally decided on.
    """

    CATEGORY_CHOICES = [
        ("policy",         "Policy"),
        ("welfare",        "Student Welfare"),
        ("academic",       "Academic Affairs"),
        ("infrastructure", "Infrastructure and Facilities"),
        ("financial",      "Financial / Fees"),
        ("events",         "Events and Activities"),
        ("other",          "Other"),
    ]

    STATUS_CHOICES = [
        ("submitted",     "Submitted"),
        ("under_review",  "Under Review"),
        ("approved",      "Approved"),
        ("rejected",      "Rejected"),
        ("implemented",   "Implemented"),
    ]

    term = models.ForeignKey(
        "CouncilTerm",
        on_delete=models.CASCADE,
        related_name="proposals",
    )

    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )
    description = models.TextField()

    submitted_by = models.ForeignKey(
        "Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_proposals",
    )

    sponsoring_position = models.ForeignKey(
        "CouncilPosition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sponsored_proposals",
        help_text="Council member championing this proposal, if any.",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="submitted",
        db_index=True,
    )

    submitted_at = models.DateTimeField(default=timezone.now)

    decided_by = models.ForeignKey(
        "CouncilPosition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_proposals",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Council Proposal"
        verbose_name_plural = "Council Proposals"

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    @property
    def support_count(self):
        return self.supporters.count()

    def clean(self):
        super().clean()
        if self.sponsoring_position_id and self.sponsoring_position.term_id != self.term_id:
            raise ValidationError({
                "sponsoring_position": "The sponsor must be a council member from the same term."
            })
        if self.status in ("approved", "rejected", "implemented") and not self.decided_at:
            self.decided_at = timezone.now()


class ProposalSupport(BaseModelMixin):
    """A student's endorsement/upvote of a CouncilProposal."""

    proposal = models.ForeignKey(
        "CouncilProposal",
        on_delete=models.CASCADE,
        related_name="supporters",
    )
    student = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="proposal_endorsements",
    )
    supported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("proposal", "student")
        verbose_name = "Proposal Support"
        verbose_name_plural = "Proposal Supporters"

    def __str__(self):
        return f"{self.student} supports {self.proposal}"


# ─────────────────────────────────────────────────────────────────────────────
# Grievances
# ─────────────────────────────────────────────────────────────────────────────

class Grievance(BaseModelMixin):
    """
    A student grievance escalated to (or raised directly with) the Student
    Council — "Student Grievance Handling" in the sidebar. Distinct from
    a general support ticket in that it's routed to a specific council
    portfolio holder rather than an admin help desk.
    """

    CATEGORY_CHOICES = [
        ("academic",     "Academic"),
        ("welfare",      "Welfare"),
        ("harassment",   "Harassment / Misconduct"),
        ("facilities",   "Facilities"),
        ("financial",    "Financial / Fees"),
        ("disciplinary", "Disciplinary Process"),
        ("other",        "Other"),
    ]

    STATUS_CHOICES = [
        ("submitted",    "Submitted"),
        ("under_review", "Under Review"),
        ("escalated",    "Escalated to Administration"),
        ("resolved",     "Resolved"),
        ("dismissed",    "Dismissed"),
    ]

    term = models.ForeignKey(
        "CouncilTerm",
        on_delete=models.CASCADE,
        related_name="grievances",
    )

    submitted_by = models.ForeignKey(
        "Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grievances_filed",
        help_text="Left null when is_anonymous is True to protect the submitter's identity.",
    )

    is_anonymous = models.BooleanField(default=False)

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )
    description = models.TextField()

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="submitted",
        db_index=True,
    )

    # Sensitive categories (harassment/disciplinary) get restricted
    # visibility, mirroring StudentMedicalProfile's classification pattern.
    is_sensitive = models.BooleanField(default=False)

    assigned_to = models.ForeignKey(
        "CouncilPosition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_grievances",
        help_text="Typically the Welfare Secretary, or Chairperson for escalated cases.",
    )

    submitted_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Student Grievance"
        verbose_name_plural = "Student Grievances"

    def __str__(self):
        who = "Anonymous" if self.is_anonymous else self.submitted_by
        return f"Grievance #{self.record_id} — {who} [{self.get_status_display()}]"

    def clean(self):
        super().clean()

        if self.is_anonymous and self.submitted_by_id:
            raise ValidationError({
                "submitted_by": "An anonymous grievance should not retain the submitter's identity."
            })

        if not self.is_anonymous and not self.submitted_by_id and self._state.adding:
            raise ValidationError({
                "submitted_by": "Provide a submitter, or mark the grievance as anonymous."
            })

        if self.category in ("harassment", "disciplinary"):
            self.is_sensitive = True

        if self.status == "resolved" and not self.resolved_at:
            self.resolved_at = timezone.now()


class GrievanceUpdate(BaseModelMixin):
    """
    A timeline entry on a Grievance — status changes, internal notes, or
    messages back to the submitter.
    """

    grievance = models.ForeignKey(
        "Grievance",
        on_delete=models.CASCADE,
        related_name="updates",
    )

    author = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grievance_updates_authored",
    )

    note = models.TextField()

    is_internal = models.BooleanField(
        default=True,
        help_text="If true, only visible to council members/staff handling the "
        "grievance — not to the submitter.",
    )

    class Meta:
        ordering = ["created_at"] if hasattr(
            BaseModelMixin, "created_at") else ["record_id"]
        verbose_name = "Grievance Update"
        verbose_name_plural = "Grievance Updates"

    def __str__(self):
        return f"Update on {self.grievance} by {self.author or 'system'}"


# ─────────────────────────────────────────────────────────────────────────────
# Meetings
# ─────────────────────────────────────────────────────────────────────────────

class CouncilMeeting(BaseModelMixin):
    """A scheduled Student Council meeting."""

    MEETING_TYPE_CHOICES = [
        ("regular",   "Regular Meeting"),
        ("emergency", "Emergency Meeting"),
        ("special",   "Special / Extraordinary Meeting"),
        ("joint",     "Joint Meeting with Administration"),
    ]

    STATUS_CHOICES = [
        ("scheduled",  "Scheduled"),
        ("held",       "Held"),
        ("cancelled",  "Cancelled"),
        ("postponed",  "Postponed"),
    ]

    term = models.ForeignKey(
        "CouncilTerm",
        on_delete=models.CASCADE,
        related_name="meetings",
    )

    title = models.CharField(max_length=200)
    meeting_type = models.CharField(
        max_length=15,
        choices=MEETING_TYPE_CHOICES,
        default="regular",
    )

    agenda = models.TextField(blank=True, default="")
    minutes = models.TextField(blank=True, default="")
    minutes_file = models.FileField(
        upload_to="council_minutes/",
        null=True,
        blank=True,
    )

    venue = models.ForeignKey(
        "Venue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="council_meetings",
    )
    external_location = models.CharField(
        max_length=255, blank=True, default="")

    scheduled_at = models.DateTimeField()

    chaired_by = models.ForeignKey(
        "CouncilPosition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chaired_meetings",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="scheduled",
        db_index=True,
    )

    class Meta:
        ordering = ["-scheduled_at"]
        verbose_name = "Council Meeting"
        verbose_name_plural = "Council Meetings"

    def __str__(self):
        return f"{self.title} — {self.scheduled_at:%Y-%m-%d} [{self.get_status_display()}]"

    def clean(self):
        super().clean()

        if not self.venue_id and not self.external_location:
            raise ValidationError({
                "venue": "Provide either a campus venue or an external location."
            })

        if self.chaired_by_id and self.chaired_by.term_id != self.term_id:
            raise ValidationError({
                "chaired_by": "The chair must be a council member from the same term."
            })


class CouncilMeetingAttendance(BaseModelMixin):
    """Attendance register for a CouncilMeeting."""

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent",  "Absent"),
        ("excused", "Excused"),
    ]

    meeting = models.ForeignKey(
        "CouncilMeeting",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    position_holder = models.ForeignKey(
        "CouncilPosition",
        on_delete=models.CASCADE,
        related_name="meeting_attendance",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="present",
    )

    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("meeting", "position_holder")
        verbose_name = "Council Meeting Attendance"
        verbose_name_plural = "Council Meeting Attendance Records"

    def __str__(self):
        return f"{self.position_holder.student} — {self.meeting.title} [{self.get_status_display()}]"

    def clean(self):
        super().clean()
        if self.meeting_id and self.position_holder_id and self.position_holder.term_id != self.meeting.term_id:
            raise ValidationError({
                "position_holder": "This council member is not part of the term this meeting belongs to."
            })
