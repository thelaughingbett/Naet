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
