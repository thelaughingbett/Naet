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

from .base import BaseModelMixin


class Club(BaseModelMixin):
    """
    A student club or society. Deliberately not tied to a single
    Department/School via WithDepartmentMixin/WithSchoolMixin — most clubs
    (sports, media, religious, cultural) draw membership university-wide.
    Academic/professional societies can still be scoped to a department
    via the optional `department` FK below.
    """

    CATEGORY_CHOICES = [
        ("academic",      "Academic / Professional"),
        ("sports",        "Sports and Games"),
        ("cultural",      "Cultural"),
        ("religious",     "Religious / Faith-Based"),
        ("performing_arts", "Performing Arts (Drama, Music, Dance)"),
        ("media",         "Media and Journalism"),
        ("community",     "Community Service / Volunteering"),
        ("environment",   "Environment and Conservation"),
        ("entrepreneurship", "Entrepreneurship and Innovation"),
        ("political",     "Political / Debate"),
        ("special_interest", "Special Interest / Hobby"),
    ]

    STATUS_CHOICES = [
        ("active",     "Active"),
        ("dormant",    "Dormant / Inactive"),
        ("suspended",  "Suspended"),
        ("dissolved",  "Dissolved"),
    ]

    name = models.CharField(max_length=150, unique=True)

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short registry code, e.g. 'CS-CLUB', 'DRAMA-SOC'."
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="special_interest",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="active",
    )

    description = models.TextField(blank=True, default="")

    logo = models.ImageField(
        upload_to="club_logos/",
        null=True,
        blank=True,
    )

    # Optional scoping — set only for department/school-affiliated societies
    # (e.g. a departmental academic society). Left null for open,
    # university-wide clubs.
    department = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="affiliated_clubs",
    )

    # Staff members formally accountable for the club to the Dean of
    # Students' office. A club may have several (main patron + co-patrons);
    # exactly one is flagged primary at a time — see ClubPatron. Distinct
    # from day-to-day student leadership, which is tracked via
    # ClubLeadershipPosition below.
    patrons = models.ManyToManyField(
        "User",
        through="ClubPatron",
        related_name="patronized_clubs",
        blank=True,
    )

    founded_date = models.DateField(null=True, blank=True)

    default_meeting_venue = models.ForeignKey(
        "Venue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_clubs",
    )

    membership_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional cap on active membership. Leave blank for no cap.",
    )

    annual_dues = models.PositiveIntegerField(
        default=0,
        help_text="KES. 0 means the club charges no membership dues.",
    )

    members = models.ManyToManyField(
        "Student",
        through="ClubMembership",
        related_name="clubs",
        blank=True,
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = "Club / Society"
        verbose_name_plural = "Clubs / Societies"

    def __str__(self):
        return self.name

    @property
    def active_member_count(self):
        return self.club_memberships.filter(status="active").count()

    @property
    def is_full(self):
        if not self.membership_capacity:
            return False
        return self.active_member_count >= self.membership_capacity

    @property
    def current_leadership(self):
        """Currently-serving leadership roster, most senior positions first."""
        return self.leadership_positions.filter(
            is_active=True
        ).select_related("member__student__user").order_by("position")

    @property
    def current_patrons(self):
        """Active patron assignments, primary patron first."""
        return self.club_patrons.filter(
            is_active=True
        ).select_related("staff").order_by("-is_primary", "role")

    @property
    def primary_patron(self):
        assignment = self.club_patrons.filter(
            is_active=True, is_primary=True
        ).select_related("staff").first()
        return assignment.staff if assignment else None

    def clean(self):
        super().clean()
        if self.status == "dissolved" and self.leadership_positions.filter(is_active=True).exists():
            raise ValidationError({
                "status": "A dissolved club cannot have active leadership positions. "
                          "Close out leadership terms first."
            })


class ClubPatron(BaseModelMixin):
    """
    Through-table linking staff Users to a Club as patrons/advisors.
    A club can have several (main patron + co-patrons/assistant patrons),
    but exactly one active assignment is flagged as primary — the one
    formally accountable to the Dean of Students' office.
    """

    ROLE_CHOICES = [
        ("patron",           "Patron"),
        ("co_patron",        "Co-Patron"),
        ("assistant_patron", "Assistant Patron"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="club_patrons",
    )

    staff = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name="club_patron_assignments",
        limit_choices_to={"is_staff": True},
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="co_patron",
    )

    is_primary = models.BooleanField(
        default=False,
        help_text="The single patron formally accountable for the club. "
        "Only one active primary is allowed per club.",
    )

    date_appointed = models.DateField(default=timezone.now)
    date_ended = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    notes = models.CharField(max_length=255, blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        constraints = [
            # Only one active primary patron per club at a time.
            models.UniqueConstraint(
                fields=["club"],
                condition=models.Q(is_active=True, is_primary=True),
                name="unique_active_primary_patron_per_club",
            )
        ]
        unique_together = ("club", "staff")
        ordering = ["club", "-is_primary", "role"]
        verbose_name = "Club Patron"
        verbose_name_plural = "Club Patrons"

    def __str__(self):
        role = "Primary Patron" if self.is_primary else self.get_role_display()
        return f"{self.staff.get_full_name()} — {self.club} ({role})"

    def clean(self):
        super().clean()

        if not self.staff_id:
            return

        if not self.staff.is_staff:
            raise ValidationError({
                "staff": "Only a staff user account can be assigned as a club patron."
            })

        if self.is_primary and self.is_active:
            clashing_primary = ClubPatron.objects.filter(
                club=self.club,
                is_primary=True,
                is_active=True,
            ).exclude(pk=self.pk)

            if clashing_primary.exists():
                raise ValidationError({
                    "is_primary": "This club already has an active primary patron. "
                                  "Demote the existing one first, or add this patron "
                                  "as a co-patron/assistant patron instead."
                })

        if self.date_ended and self.date_appointed and self.date_ended < self.date_appointed:
            raise ValidationError({
                "date_ended": "End date cannot be earlier than the appointment date."
            })

        if self.date_ended and self.is_active:
            raise ValidationError({
                "is_active": "A patron assignment with an end date should not remain marked active."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ClubMembership(BaseModelMixin):
    """
    Through-table linking a Student to a Club. Holds membership lifecycle
    state separately from any leadership role, which is tracked via
    ClubLeadershipPosition (a member can hold a leadership position, but
    the membership row itself only tracks rank-and-file status).
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


class ClubEvent(BaseModelMixin):
    """
    A meeting, activity, competition, or community-service outing organised
    by a club. Attendance is tracked via ClubEventAttendance.
    """

    EVENT_TYPE_CHOICES = [
        ("meeting",     "Regular Meeting"),
        ("agm",         "Annual General Meeting"),
        ("training",    "Training / Workshop"),
        ("competition", "Competition / Tournament"),
        ("community_service", "Community Service"),
        ("social",      "Social Event"),
        ("fundraiser",  "Fundraiser"),
        ("other",       "Other"),
    ]

    APPROVAL_STATUS_CHOICES = [
        ("draft",             "Draft"),
        ("pending_approval",  "Pending Dean of Students' Approval"),
        ("approved",          "Approved"),
        ("rejected",          "Rejected"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="events",
    )

    title = models.CharField(max_length=200)
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default="meeting",
    )

    description = models.TextField(blank=True, default="")

    venue = models.ForeignKey(
        "Venue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_events",
    )

    # Used when a club event happens off-campus (e.g. inter-university
    # tournament) and there's no Venue record for it.
    external_location = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(
        null=True,
        blank=True
    )

    is_mandatory = models.BooleanField(
        default=False,
        help_text="If true, absence may affect membership standing.",
    )

    organized_by = models.ForeignKey(
        "ClubMembership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organized_events",
    )

    # "Event Approval Requests (to Dean)" workflow — events start as Draft,
    # get submitted for review, and are approved/rejected by a member of
    # the Dean of Students'/Student Affairs office before they're allowed
    # to appear on the public events feed.
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default="draft",
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_events_reviewed",
        limit_choices_to={"is_staff": True},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-start_time"]
        verbose_name = "Club Event"
        verbose_name_plural = "Club Events"

    def __str__(self):
        return f"{self.club} — {self.title} ({self.start_time:%Y-%m-%d})"

    def clean(self):
        super().clean()

        if not self.venue_id and not self.external_location:
            raise ValidationError({
                "venue": "Provide either a campus venue or an external location."
            })

        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError({
                "end_time": "End time must be after the start time."
            })

        if self.organized_by_id and self.organized_by.club_id != self.club_id:
            raise ValidationError({
                "organized_by": "The organizer must be a member of this club."
            })

        if self.approval_status == "rejected" and not self.rejection_reason:
            raise ValidationError({
                "rejection_reason": "A reason is required when rejecting an event request."
            })

    def submit_for_approval(self):
        """Move a draft event into the Dean's review queue."""
        if self.approval_status != "draft":
            return
        self.approval_status = "pending_approval"
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, by_user):
        if self.approval_status != "pending_approval":
            return
        self.approval_status = "approved"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = ""
        self.save()

    def reject(self, by_user, reason):
        if self.approval_status != "pending_approval":
            return
        self.approval_status = "rejected"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class ClubEventAttendance(BaseModelMixin):
    """Attendance register for a ClubEvent."""

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent",  "Absent"),
        ("excused", "Excused"),
    ]

    event = models.ForeignKey(
        "ClubEvent",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    member = models.ForeignKey(
        "ClubMembership",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="present",
    )

    marked_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_attendance_marked",
        help_text="Executive member or patron who took the register.",
    )

    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("event", "member")
        verbose_name = "Club Event Attendance"
        verbose_name_plural = "Club Event Attendance Records"

    def __str__(self):
        return f"{self.member.student} — {self.event.title} [{self.get_status_display()}]"

    def clean(self):
        super().clean()
        if self.event_id and self.member_id and self.member.club_id != self.event.club_id:
            raise ValidationError({
                "member": "This member does not belong to the club hosting this event."
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


class ClubBudget(BaseModelMixin):
    """
    A club's approved financial envelope for a given Session — "Club
    Budget & Expenses" in the Club Management sidebar. Actual income and
    spend against it is tracked via ClubTransaction.
    """

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="budgets",
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name="club_budgets",
    )

    allocated_amount = models.PositiveIntegerField(
        default=0,
        help_text="KES. Approved allocation for this club for this session "
        "(e.g. from a Student Council/Dean of Students grant).",
    )

    notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ("club", "session")
        verbose_name = "Club Budget"
        verbose_name_plural = "Club Budgets"

    def __str__(self):
        return f"{self.club} — {self.session} budget"

    @property
    def total_income(self):
        total = self.transactions.filter(
            transaction_type="income", status="approved"
        ).aggregate(total=models.Sum("amount"))["total"]
        return total or 0

    @property
    def total_expenses(self):
        total = self.transactions.filter(
            transaction_type="expense", status="approved"
        ).aggregate(total=models.Sum("amount"))["total"]
        return total or 0

    @property
    def balance(self):
        return self.allocated_amount + self.total_income - self.total_expenses


class ClubTransaction(BaseModelMixin):
    """
    A single income or expense line item for a club — feeds the "Club
    Budget & Expenses" view. Tied to a ClubBudget where one exists for the
    session; a club can still log transactions without a formal budget
    (e.g. informal fundraiser proceeds), so `budget` is optional.
    """

    TRANSACTION_TYPE_CHOICES = [
        ("income",  "Income"),
        ("expense", "Expense"),
    ]

    CATEGORY_CHOICES = [
        ("dues",         "Membership Dues"),
        ("fundraiser",   "Fundraiser"),
        ("sponsorship",  "Sponsorship"),
        ("grant",        "Institutional Grant"),
        ("event_cost",   "Event Cost"),
        ("equipment",    "Equipment / Supplies"),
        ("transport",    "Transport"),
        ("refreshments", "Refreshments"),
        ("other",        "Other"),
    ]

    STATUS_CHOICES = [
        ("draft",    "Draft"),
        ("pending",  "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    budget = models.ForeignKey(
        "ClubBudget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )

    amount = models.PositiveIntegerField(help_text="KES")
    description = models.CharField(max_length=255)

    receipt = models.FileField(
        upload_to="club_transactions/",
        null=True,
        blank=True,
    )

    # Typically the club's treasurer, but any exec member can log a
    # transaction for review.
    recorded_by = models.ForeignKey(
        "ClubMembership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_transactions",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_transactions_reviewed",
        limit_choices_to={"is_staff": True},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    transacted_at = models.DateField(default=timezone.now)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-transacted_at"]
        verbose_name = "Club Transaction"
        verbose_name_plural = "Club Transactions"

    def __str__(self):
        sign = "+" if self.transaction_type == "income" else "-"
        return f"{self.club} — {sign}KES {self.amount} ({self.description})"

    def clean(self):
        super().clean()

        if self.budget_id and self.budget.club_id != self.club_id:
            raise ValidationError({
                "budget": "This budget belongs to a different club."
            })

        if self.recorded_by_id and self.recorded_by.club_id != self.club_id:
            raise ValidationError({
                "recorded_by": "The recorder must be a member of this club."
            })

    def approve(self, by_user):
        if self.status != "pending":
            return
        self.status = "approved"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, by_user):
        if self.status != "pending":
            return
        self.status = "rejected"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save()


class ClubActivityReport(BaseModelMixin):
    """
    A club's periodic activity report to the Dean of Students'/Student
    Affairs office — "Activity Reports" in the Club Management sidebar.
    """

    STATUS_CHOICES = [
        ("draft",     "Draft"),
        ("submitted", "Submitted"),
        ("reviewed",  "Reviewed"),
        ("approved",  "Approved"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="activity_reports",
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name="club_activity_reports",
    )

    title = models.CharField(max_length=200)
    summary = models.TextField()

    attachment = models.FileField(
        upload_to="club_reports/",
        null=True,
        blank=True,
    )

    submitted_by = models.ForeignKey(
        "ClubMembership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_reports",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_reports_reviewed",
        limit_choices_to={"is_staff": True},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ("club", "session", "title")
        ordering = ["-submitted_at"]
        verbose_name = "Club Activity Report"
        verbose_name_plural = "Club Activity Reports"

    def __str__(self):
        return f"{self.club} — {self.title} ({self.session}) [{self.get_status_display()}]"

    def clean(self):
        super().clean()
        if self.submitted_by_id and self.submitted_by.club_id != self.club_id:
            raise ValidationError({
                "submitted_by": "The submitter must be a member of this club."
            })

    def submit(self, by_member):
        if self.status != "draft":
            return
        self.status = "submitted"
        self.submitted_by = by_member
        self.submitted_at = timezone.now()
        self.save()
