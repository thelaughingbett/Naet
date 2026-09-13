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
# ElectionPosition (in elections.py — what's being contested) so the two
# stay in lockstep.
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
    outcomes are installed here via Election.declare_winners() (elections.py).
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
