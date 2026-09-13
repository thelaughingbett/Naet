# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Scheduling domain — the master weekly timetable of regular classes
(Timetable) and the day-to-day record of whether each slot actually
happened, was rescheduled, or was missed (DailyClassExecution).

Distinct from exams.exam_scheduling: this is ordinary lecture/practical/
CAT/tutorial scheduling, recurring weekly against a Curriculum slot,
not a one-off exam sitting. Both domains depend on facilities.Venue,
which is why Venue lives in its own subpackage rather than either one.
"""

from django.core.exceptions import ValidationError
from django.db import models

from ..base import BaseModelMixin


class Timetable(BaseModelMixin):

    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.PROTECT,
        related_name='timetable_slots'
    )

    # TODO : move this to settings.py
    DAY_CHOICES = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    # TODO : move this to settings.py
    TIME_SLOTS = [
        ('08:00-10:00', '1st Slot (08:00 - 10:00)'),
        ('10:00-12:00', '2nd Slot (10:00 - 12:00)'),
        ('12:00-13:00', '3rd Slot (12:00 - 13:00)'),
        ('13:00-15:00', '4th Slot (13:00 - 15:00)'),
        ('15:00-17:00', '5th Slot (15:00 - 17:00)'),
        ('17:00-19:00', '6th Slot (17:00 - 19:00)'),
    ]

    TIMETABLE_SLOT_TYPE_CHOICES = [
        ('Lecture', 'Regular Lecture Class'),
        ('Practical', 'Practical / Laboratory Session'),
        ('CAT', 'Continuous Assessment Test (CAT)'),
        ('Tutorial', 'Tutorial / Discussion Group'),
    ]

    slot_type = models.CharField(
        max_length=15,
        choices=TIMETABLE_SLOT_TYPE_CHOICES,
        default='Lecture',
        db_index=True,
        help_text="Tracks session allocation styles required for specialized capacity audits."
    )

    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    time_slot = models.CharField(max_length=11, choices=TIME_SLOTS)

    venue = models.ForeignKey(
        "Venue",
        on_delete=models.DO_NOTHING,
        related_name="timetable_slots"
    )

    class Meta:
        unique_together = [
            # Prevent a cohort from being split into two slots at once
            ('curriculum', 'day', 'time_slot'),
            # Prevent double-booking a single physical venue space
            ('venue', 'day', 'time_slot'),
        ]
        verbose_name = "Master Timetable Slot"
        verbose_name_plural = "Master Timetable Slots"

    def clean(self):
        """
        Compliance Audit: Verifies space limitations and facility traits 
        against the designated slot requirements.
        """
        super().clean()

        if self.venue_id and self.curriculum_id:
            # 1. Computer Lab Resource Safe-Check
            # If the class is flagged as a Practical/Lab session, ensure the assigned venue actually has computers.
            if self.slot_type == 'Practical' and not self.venue.has_computers:
                raise ValidationError({
                    'venue': f"Resource Defieciency: Cannot assign a 'Practical' slot type to '{self.venue.venue_name}' "
                    f"because this venue record indicates it lacks computer/lab workstations."
                })

            # 2. Strict Class Capacity Guardrail
            # Ensure the cohort student size (Tclass size) does not exceed the maximum physical sitting limits of the venue.
            # Assuming a student_count tracker exists on Tclass
            cohort_size = self.curriculum.Tclass.student_count
            if cohort_size > self.venue.capacity:
                raise ValidationError({
                    'venue': f"Capacity Breach: The cohort class size ({cohort_size} students) exceeds "
                    f"the maximum legal capacity of '{self.venue.venue_name}' ({self.venue.capacity} seats)."
                })

    def __str__(self):
        return f"{self.curriculum.course.course_code} ({self.slot_type}) — {self.day} [{self.time_slot}]"


EXECUTION_STATUS_CHOICES = [
    ('Scheduled', 'Scheduled (Default state for the day)'),
    ('Attended', 'Attended / Successfully Taught'),
    ('Missed', 'Missed / Lecturer No-Show'),
    ('Cancelled', 'Cancelled / General University Holiday'),
    ('Rescheduled', 'Rescheduled to a New Slot'),
]

RESCHEDULE_INITIATOR_CHOICES = [
    ('LECTURER', 'Requested by Assigned Faculty/Lecturer'),
    ('STUDENT', 'Requested by Student Cohort / Class Rep'),
    ('ADMIN', 'Enforced by University Administration'),
]


class DailyClassExecution(BaseModelMixin):
    """
    Tracks the actual day-to-day execution and attendance of a timetable slot.
    Feeds directly into CUE quality audits for class contact-hour verification.
    """
    timetable_slot = models.ForeignKey(
        'Timetable',
        on_delete=models.PROTECT,
        related_name='daily_executions'
    )

    # The actual calendar date for this specific lecture instance
    calendar_date = models.DateField(db_index=True)

    # Updated to point directly to the list variable
    status = models.CharField(
        max_length=20,
        choices=EXECUTION_STATUS_CHOICES,
        default='Scheduled',
        db_index=True
    )

    # --- STUDENT ATTENDANCE CONFIRMATION ENGINE ---
    class_representative = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='confirmed_daily_classes',
        null=True,
        blank=True,
        help_text="The Class Representative or student who signs off/vouchers that the class took place."
    )

    student_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True
    )

    # --- RESCHEDULING ENGINE METRICS ---
    rescheduled_by = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name='initiated_class_reschedules',
        null=True,
        blank=True,
        help_text="The staff user (lecturer/admin) who processed the adjustment in the system."
    )

    # Updated to point directly to the list variable
    reschedule_requested_by_role = models.CharField(
        max_length=15,
        choices=RESCHEDULE_INITIATOR_CHOICES,
        null=True,
        blank=True,
        help_text="Tracks whether the request came from the lecturer or the student group."
    )

    # The new target coordinates if status == 'Rescheduled'
    rescheduled_to_date = models.DateField(null=True, blank=True)
    rescheduled_to_time_slot = models.CharField(
        max_length=11,
        choices=Timetable.TIME_SLOTS,  # Reuses choices array from your main Timetable class
        null=True,
        blank=True
    )

    rescheduled_to_venue = models.ForeignKey(
        'Venue',
        on_delete=models.PROTECT,
        related_name='rescheduled_classes',
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True,
        help_text="Reasoning for cancellation or rescheduling parameters."
    )

    class Meta:
        unique_together = ('timetable_slot', 'calendar_date')
        verbose_name = "Daily Class Execution"
        verbose_name_plural = "Daily Class Executions"
        ordering = ['-calendar_date']

    def clean(self):
        """
        Enforces strict logical guardrails over class sign-offs and reschedule moves.
        """
        super().clean()

        # 1. Verification Guardrail
        if self.status == 'Attended':
            if not self.class_representative:
                raise ValidationError({
                    'class_representative': "CUE Academic Audit Rule: Cannot log a lecture instance as 'Attended' "
                                            "without assigning a verifying Student representative code."
                })
            if not self.student_confirmed_at:
                from django.utils import timezone
                self.student_confirmed_at = timezone.now()

        # 2. Rescheduling Data Integrity Guardrail
        if self.status == 'Rescheduled':
            if not self.rescheduled_by or not self.reschedule_requested_by_role:
                raise ValidationError({
                    'rescheduled_by': "Please document the user and requesting role initiating this reschedule event."
                })
            if not self.rescheduled_to_date or not self.rescheduled_to_time_slot or not self.rescheduled_to_venue:
                raise ValidationError({
                    'rescheduled_to_date': "You must complete all target fields (Date, Time, and Venue) when moving a class."
                })

            # Prevent moving a class onto the exact same coordinates
            if (self.calendar_date == self.rescheduled_to_date and
                self.timetable_slot.time_slot == self.rescheduled_to_time_slot and
                    self.timetable_slot.venue == self.rescheduled_to_venue):
                raise ValidationError(
                    "Invalid Reschedule: Target coordinates match the original slot parameters.")

    def __str__(self):
        return f"{self.calendar_date} : {self.timetable_slot.curriculum.course.course_code} -> [{self.get_status_display()}]"
