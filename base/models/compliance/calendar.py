# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Compliance calendar domain — a denormalized projection over
Accreditation, RegulatoryReport, and RegistrationWindow deadlines, so
a calendar view can query one table instead of joining three.

This is the file that ties the rest of the `compliance` subpackage
together: `SOURCE_TYPE_CHOICES` names the exact three models the other
files in this subpackage define (accreditation.py, registration_windows.py,
regulatory_reports.py), which is why all four live under one subpackage
rather than being scattered across whichever domain each source model
felt closest to.

Regenerate via a management command / signal whenever a source
record's date fields change — this table is not hand-maintained, and
nothing in this file itself keeps it in sync.
"""

from django.db import models

from ..base import BaseModelMixin


SOURCE_TYPE_CHOICES = [
    ("accreditation_expiry", "Accreditation Expiry"),
    ("report_deadline", "Report Deadline"),
    ("registration_window", "Registration Window"),
]

RECURRENCE_CHOICES = [
    ("none", "None"),
    ("semester", "Semester"),
    ("annual", "Annual"),
]


class ComplianceCalendarEvent(BaseModelMixin):
    """
    A denormalized projection over Accreditation, RegulatoryReport, and
    RegistrationWindow deadlines, so the calendar view can query one table
    instead of joining three. Regenerate via a management command / signal
    whenever a source record's date fields change — don't hand-maintain.
    """

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPE_CHOICES
    )

    # Generic-ish pointer without full GenericForeignKey overhead; app-level
    # code resolves source_id against the right model based on source_type.
    source_id = models.CharField(max_length=30, )

    title = models.CharField(max_length=255)
    due_date = models.DateField(db_index=True)

    recurrence = models.CharField(
        max_length=20,
        choices=RECURRENCE_CHOICES,
        default="none"
    )

    class Meta:
        ordering = ["due_date"]
        indexes = [
            models.Index(fields=["source_type", "source_id"])
        ]

    def __str__(self):
        return f"{self.title} ({self.due_date})"

    def days_remaining(self):
        from django.utils import timezone
        return (self.due_date - timezone.now().date()).days
