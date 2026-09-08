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
from .club import Club  # needed directly (not just string FK) by
# ClubLeadershipPosition.clubs_administered_by() below, which returns
# a real Club queryset rather than working through a related manager.


class ClubMembership(BaseModelMixin):
    """
    Through-table linking a Student to a Club. Holds membership lifecycle
    state separately from any leadership role, which is tracked via
    ClubLeadershipPosition below (a member can hold a leadership position,
    but the membership row itself only tracks rank-and-file status).
    """

    STATUS_CHOICES = [
        ("pending",   "Pending Approval"),
        ("active",    "Active"),
        ("inactive",  "Inactive"),
        ("suspended", "Suspended"),
        ("alumni",    "Alumni / Graduated"),
        ("withdrawn", "Withdrawn"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="club_memberships",
    )

    student = models.ForeignKey(
        "Student",
        on_delete=models.CASCADE,
        related_name="club_memberships",
    )

    # Set when the application came in through an active recruitment
    # window rather than an ad-hoc "join requests" submission. Left null
    # for walk-in/rolling applications.
    recruitment_drive = models.ForeignKey(
        "ClubRecruitmentDrive",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )

    motivation = models.TextField(
        blank=True,
        default="",
        help_text="Optional note from the applicant on why they want to join.",
    )

    membership_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Assigned once the membership is approved, e.g. 'CS-CLUB/0042'.",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    date_joined = models.DateField(default=timezone.now)
    date_left = models.DateField(null=True, blank=True)

    dues_paid = models.BooleanField(default=False)

    # Who actioned the pending application/status change, e.g. via
    # "Membership Approvals" in the Club Management sidebar section —
    # typically an exec member's User, occasionally a patron.
    reviewed_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_membership_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ("club", "student")
        verbose_name = "Club Membership"
        verbose_name_plural = "Club Memberships"

    def __str__(self):
        return f"{self.student} — {self.club} [{self.get_status_display()}]"

    def clean(self):
        super().clean()

        if self.status == "active":
            if self.club_id and self.club.is_full and self._state.adding:
                raise ValidationError(
                    f"{self.club} has reached its membership capacity "
                    f"({self.club.membership_capacity})."
                )

        if self.recruitment_drive_id and self.club_id and self.recruitment_drive.club_id != self.club_id:
            raise ValidationError({
                "recruitment_drive": "This recruitment drive belongs to a different club."
            })

        if self.status in ("alumni", "withdrawn") and not self.date_left:
            self.date_left = timezone.now().date()

    def approve(self, by_user=None):
        """Activate a pending membership, assigning a membership number."""
        if self.status != "pending":
            return
        self.status = "active"
        if not self.membership_number:
            count = ClubMembership.objects.filter(
                club=self.club
            ).exclude(pk=self.pk).count()
            self.membership_number = f"{self.club.code}/{count + 1:04d}"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, by_user=None, reason=""):
        """Decline a pending application without creating a membership record."""
        if self.status != "pending":
            return
        self.status = "withdrawn"
        self.rejection_reason = reason
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save()


class ClubLeadershipPosition(BaseModelMixin):
    """
    Tracks student leadership terms within a club (Chair, Secretary,
    Treasurer, etc.) — mirrors AcademicAppointment's pattern of one active
    holder per (club, position) at a time.
    """

    POSITION_CHOICES = [
        ("chairperson",     "Chairperson / President"),
        ("vice_chair",      "Vice Chairperson / Vice President"),
        ("secretary",       "Secretary General"),
        ("assistant_secretary", "Assistant Secretary"),
        ("treasurer",       "Treasurer"),
        ("organizing_sec",  "Organizing Secretary"),
        ("publicity_sec",   "Publicity Secretary"),
        ("committee_member", "Committee Member"),
    ]

    # Positions that should unlock the "Club Management" sidebar section
    # (the `club_head` role) — everything except a bare committee seat.
    ADMIN_POSITIONS = {
        "chairperson",
        "vice_chair",
        "secretary",
        "assistant_secretary",
        "treasurer",
        "organizing_sec",
        "publicity_sec",
    }

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="leadership_positions",
    )

    member = models.ForeignKey(
        "ClubMembership",
        on_delete=models.CASCADE,
        related_name="leadership_terms",
        help_text="Must be an active member of the same club.",
    )

    position = models.CharField(
        max_length=30,
        choices=POSITION_CHOICES,
    )

    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Only one active holder of a given position per club at a time
            # (committee_member is deliberately excluded from this rule,
            # since a club may have several committee members concurrently).
            models.UniqueConstraint(
                fields=["club", "position"],
                condition=models.Q(is_active=True) & ~models.Q(
                    position="committee_member"
                ),
                name="unique_active_club_position",
            )
        ]
        ordering = ["club", "position"]
        verbose_name = "Club Leadership Position"
        verbose_name_plural = "Club Leadership Positions"

    def __str__(self):
        return f"{self.get_position_display()} — {self.club} ({self.member.student})"

    @property
    def grants_admin_access(self):
        """Whether holding this position should surface Club Management
        tooling (approvals, budget, events, reports) for this student."""
        return self.position in self.ADMIN_POSITIONS

    @classmethod
    def clubs_administered_by(cls, student):
        """Clubs where `student` currently holds an admin-granting position
        — i.e. the set that should drive the `club_head` role check."""
        club_ids = cls.objects.filter(
            member__student=student,
            member__status="active",
            is_active=True,
            position__in=cls.ADMIN_POSITIONS,
        ).values_list("club_id", flat=True)
        return Club.objects.filter(record_id__in=club_ids)

    def clean(self):
        super().clean()

        if self.member_id and self.club_id and self.member.club_id != self.club_id:
            raise ValidationError({
                "member": "This membership record belongs to a different club."
            })

        if self.member_id and self.member.status != "active":
            raise ValidationError({
                "member": "Only an active club member can hold a leadership position."
            })

        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "End date cannot be earlier than the start date."
            })


class ClubRecruitmentDrive(BaseModelMixin):
    """
    A defined recruitment window for a club — "Recruitment Drive" in the
    Club Management sidebar. Applications received while a drive is open
    can be tagged against it via ClubMembership.recruitment_drive, but a
    club can still accept rolling/walk-in applications outside any drive.
    """

    STATUS_CHOICES = [
        ("upcoming",  "Upcoming"),
        ("open",      "Open"),
        ("closed",    "Closed"),
        ("cancelled", "Cancelled"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="recruitment_drives",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")

    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()

    target_intake = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Planned number of new members to recruit. Optional.",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="upcoming",
        db_index=True,
    )

    created_by = models.ForeignKey(
        "ClubMembership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_recruitment_drives",
    )

    class Meta:
        ordering = ["-opens_at"]
        verbose_name = "Club Recruitment Drive"
        verbose_name_plural = "Club Recruitment Drives"

    def __str__(self):
        return f"{self.club} — {self.title} [{self.get_status_display()}]"

    @property
    def is_currently_open(self):
        now = timezone.now()
        return self.status == "open" and self.opens_at <= now <= self.closes_at

    @property
    def application_count(self):
        return self.applications.count()

    def clean(self):
        super().clean()

        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValidationError({
                "closes_at": "Closing time must be after the opening time."
            })

        if self.created_by_id and self.created_by.club_id != self.club_id:
            raise ValidationError({
                "created_by": "The creator must be a member of this club."
            })
