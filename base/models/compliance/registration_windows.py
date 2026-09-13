# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Registration window domain — the open/close period governing when
students can act on something institution-wide: course registration,
bursary applications, hostel allocation, exam registration, backlog
exams, graduation candidacy, club membership, scholarships.

Kept in `compliance/` rather than `academics/` even though course
registration is its most heavily-used window (see
`academics/enrollment.py`'s `Enrollment.clean()`, which looks one up):
a RegistrationWindow isn't owned by any one domain it gates, and it's
one of the three source types `ComplianceCalendarEvent` denormalizes
(alongside Accreditation and RegulatoryReport) — see calendar.py.
"""

from django.db import models

from ..base import BaseModelMixin


class RegistrationWindow(BaseModelMixin):
    window_choices = [
        ("course_registration", "Course Registration"),
        ("bursary", "Bursary/Financial Aid Registration"),
        ("hostel", "Hostel Allocation"),
        ("exam_registration", "Exam Registration"),
        ("backlog_exam", "Backlog/Supplementary Exam Registration"),
        ("graduation_candidacy", "Graduation Candidacy Nomination"),
        ("club_membership", "Club Membership Drive"),
        ("scholarship", "Scholarship Application"),
    ]

    session = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="registration_windows",
        help_text="e.g. Semester 2 2026/2027",
    )
    window_type = models.CharField(
        max_length=30,
        choices=window_choices,
        help_text="What this window governs, e.g. course registration, bursary",
    )
    programme = models.ForeignKey(
        "Programme",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="registration_windows",
        help_text="Optional: restrict this window to one program. Leave blank for institution-wide.",
    )
    opens_date = models.DateField()
    closes_date = models.DateField()
    late_closes_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional grace/late period end date, if late registration is allowed (often with a penalty fee).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Manual kill-switch to close a window early regardless of dates.",
    )

    class Meta:
        ordering = ["-opens_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "window_type", "programme"],
                name="unique_window_per_session_type_program",
            )
        ]

    def __str__(self):
        scope = f" - {self.programme}" if self.programme_id else ""
        return f"{self.get_window_type_display()} ({self.session}){scope}"

    @property
    def is_open(self):
        from django.utils import timezone
        today = timezone.now().date()
        end = self.late_closes_date or self.closes_date
        return self.is_active and self.opens_date <= today <= end

    @property
    def is_late_period(self):
        from django.utils import timezone
        today = timezone.now().date()
        return bool(
            self.late_closes_date
            and self.closes_date < today <= self.late_closes_date
        )
