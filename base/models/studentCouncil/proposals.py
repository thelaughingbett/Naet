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

from ..base import BaseModelMixin


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
