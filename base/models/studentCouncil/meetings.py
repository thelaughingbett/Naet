# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.core.exceptions import ValidationError
from django.db import models

from ..base import BaseModelMixin


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
