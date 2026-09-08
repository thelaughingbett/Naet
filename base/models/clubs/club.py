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

    name = models.CharField(
        max_length=150,
        unique=True
    )

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

    description = models.TextField(
        blank=True,
        default=""
    )

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
    # ClubLeadershipPosition (membership.py).
    patrons = models.ManyToManyField(
        "User",
        through="ClubPatron",
        related_name="patronized_clubs",
        blank=True,
    )

    founded_date = models.DateField(
        null=True,
        blank=True
    )

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
