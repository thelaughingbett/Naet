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

    # NOTE: preserved as-written rather than "fixed" — this hasattr check
    # is itself evidence the original author wasn't certain whether
    # BaseModelMixin provides created_at. Grievance.__str__ above confirms
    # record_id definitely exists (it's used directly, unconditionally,
    # with no hasattr guard). created_at is still unconfirmed. Once it's
    # confirmed one way or the other, this should just be a plain
    # ordering = [...] with no runtime branch — a Meta class evaluating
    # hasattr() against another model at import time to hedge on a field
    # that may or may not exist is fragile: if BaseModelMixin ever adds
    # created_at later, this ordering silently changes with no code
    # change and no test necessarily catching it.
    class Meta:
        ordering = ["created_at"] if hasattr(
            BaseModelMixin, "created_at") else ["record_id"]
        verbose_name = "Grievance Update"
        verbose_name_plural = "Grievance Updates"

    def __str__(self):
        return f"Update on {self.grievance} by {self.author or 'system'}"
