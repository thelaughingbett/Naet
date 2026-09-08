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
