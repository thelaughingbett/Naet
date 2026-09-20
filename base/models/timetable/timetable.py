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
        related_name="timetable_slots",
        help_text="Default venue for this slot. For a shared curriculum "
        "spanning several classes, an individual class can be pinned to "
        "a different venue via TimetableClassVenue — this stays the "
        "fallback for any class without an override."
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

    def venue_for(self, class_link):
        """
        The effective venue for one class attending this slot — its own
        TimetableClassVenue override if one exists, else this slot's
        default `venue`.
        """
        override = self.class_venues.filter(class_link=class_link).first()
        return override.venue if override else self.venue

    def clean(self):
        """
        Compliance Audit: Verifies space limitations and facility traits
        against the designated slot requirements — checked per class
        attending this slot, since a shared curriculum can have several
        classes, each potentially in a different venue.
        """
        super().clean()

        if not self.curriculum_id:
            return

        class_links = self.curriculum.class_links.select_related('Tclass')

        for link in class_links:
            venue = self.venue_for(link)
            if not venue:
                continue

            # 1. Computer Lab Resource Safe-Check
            if self.slot_type == 'Practical' and not venue.has_computers:
                raise ValidationError({
                    'venue': f"Resource Deficiency: Cannot assign a 'Practical' slot type to "
                    f"'{venue.venue_name}' for {link.Tclass.class_name} because this venue "
                    f"record indicates it lacks computer/lab workstations."
                })

            # 2. Strict Class Capacity Guardrail
            cohort_size = link.Tclass.student_count
            if cohort_size > venue.capacity:
                raise ValidationError({
                    'venue': f"Capacity Breach: {link.Tclass.class_name} ({cohort_size} students) "
                    f"exceeds the maximum legal capacity of '{venue.venue_name}' "
                    f"({venue.capacity} seats)."
                })

    def __str__(self):
        return f"{self.curriculum.course.course_code} ({self.slot_type}) — {self.day} [{self.time_slot}]"


class TimetableClassVenue(BaseModelMixin):
    """
    Per-class venue override for a shared Timetable slot. A Curriculum
    can serve several classes at once (via CurriculumClass) attending
    the same lecture — for a Practical needing multiple lab rooms, or a
    common-unit cohort too large for one venue, different classes within
    the same day/time slot may need different rooms even though they
    share one Curriculum/Timetable row.
    """
    timetable_slot = models.ForeignKey(
        'Timetable',
        on_delete=models.CASCADE,
        related_name='class_venues'
    )

    class_link = models.ForeignKey(
        'CurriculumClass',
        on_delete=models.CASCADE,
        related_name='timetable_venue_overrides'
    )

    venue = models.ForeignKey(
        'Venue',
        on_delete=models.PROTECT,
        related_name='class_timetable_overrides'
    )

    class Meta:
        unique_together = ('timetable_slot', 'class_link')
        verbose_name = "Timetable Class Venue Override"

    def clean(self):
        super().clean()
        if self.class_link_id and self.timetable_slot_id:
            if self.class_link.curriculum_id != self.timetable_slot.curriculum_id:
                raise ValidationError({
                    'class_link': "This class isn't attached to the curriculum this "
                    "timetable slot belongs to."
                })
            if self.venue_id == self.timetable_slot.venue_id:
                raise ValidationError({
                    'venue': "This matches the slot's default venue — no override needed."
                })

    def __str__(self):
        return f"{self.timetable_slot} — {self.class_link.Tclass.class_name} → {self.venue.venue_name}"


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
    Tracks the actual day-to-day execution of a timetable slot — whether
    the assigned lecturer taught it, was absent, or the slot was
    cancelled/rescheduled. Feeds directly into CUE quality audits for
    class contact-hour verification.

    This is lecturer attendance, not student attendance — status answers
    "did the lecturer teach this" not "which students were present."
    class_representative below signs off that the session happened; it
    doesn't record who among students attended.

    lecturer_assignment: points at the specific LecturerAssignment this
    row is tracking attendance for, rather than at Lecturer directly —
    LecturerAssignment already carries class_link (which class, for a
    common unit split across lecturers) and status (Draft/Confirmed/
    Substituted), so this one FK carries everything needed to know both
    who and, where relevant, which class. Nullable only because it's
    auto-resolved in clean() when the slot has exactly one active
    assignment; always populated by the time the row is saved.
    """
    timetable_slot = models.ForeignKey(
        'Timetable',
        on_delete=models.PROTECT,
        related_name='daily_executions'
    )

    calendar_date = models.DateField(db_index=True)

    lecturer_assignment = models.ForeignKey(
        'LecturerAssignment',
        on_delete=models.PROTECT,
        related_name='daily_class_executions',
        null=True,
        blank=True,
        help_text="Which lecturer (and, for a common unit, which class) "
        "this row tracks attendance for. Required explicitly only when "
        "the curriculum has more than one active LecturerAssignment — "
        "otherwise resolved automatically from the slot's single one."
    )

    status = models.CharField(
        max_length=20,
        choices=EXECUTION_STATUS_CHOICES,
        default='Scheduled',
        db_index=True
    )

    class_representative = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='confirmed_daily_classes',
        null=True,
        blank=True,
        help_text="The Class Representative or student who signs off that the class took place."
    )

    student_confirmed_at = models.DateTimeField(
        null=True, blank=True, auto_now_add=True)

    rescheduled_by = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name='initiated_class_reschedules',
        null=True,
        blank=True,
    )

    reschedule_requested_by_role = models.CharField(
        max_length=15,
        choices=RESCHEDULE_INITIATOR_CHOICES,
        null=True,
        blank=True,
    )

    rescheduled_to_date = models.DateField(null=True, blank=True)
    rescheduled_to_time_slot = models.CharField(
        max_length=11,
        choices=Timetable.TIME_SLOTS,
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

    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            # One execution row per lecturer assignment per slot per date
            # — a shared curriculum with several active assignments (a
            # common unit split across lecturers) can now legitimately
            # have multiple rows for the same date, one per assignment.
            models.UniqueConstraint(
                fields=['timetable_slot', 'calendar_date',
                        'lecturer_assignment'],
                name='unique_execution_per_assignment_per_slot_per_date',
            ),
        ]
        verbose_name = "Daily Class Execution"
        verbose_name_plural = "Daily Class Executions"
        ordering = ['-calendar_date']

    def clean(self):
        super().clean()

        from base.models import LecturerAssignment

        assignments = self.timetable_slot.curriculum.lecturer_assignments.all() \
            if self.timetable_slot_id else LecturerAssignment.objects.none()

        # Substituted lecturers are no longer teaching this slot — never
        # eligible for attendance checking or auto-resolution.
        active_assignments = assignments.exclude(status='Substituted')

        if not self.lecturer_assignment_id:
            if active_assignments.count() == 1:
                self.lecturer_assignment = active_assignments.first()
            elif active_assignments.count() == 0:
                raise ValidationError({
                    'lecturer_assignment': "No active lecturer assignment exists for this "
                    "curriculum — nothing to check attendance against."
                })
            else:
                raise ValidationError({
                    'lecturer_assignment': "This curriculum has multiple active lecturer "
                    "assignments — specify which one this execution record is for."
                })

        # Confirm the referenced assignment actually belongs to this
        # timetable slot's curriculum, and hasn't since been substituted.
        elif self.lecturer_assignment.curriculum_id != self.timetable_slot.curriculum_id:
            raise ValidationError({
                'lecturer_assignment': "This assignment doesn't belong to the curriculum "
                "this timetable slot is for."
            })
        elif self.lecturer_assignment.status == 'Substituted':
            raise ValidationError({
                'lecturer_assignment': f"{self.lecturer_assignment.lecturer} has been "
                "substituted off this curriculum and can no longer be logged for "
                "attendance on it."
            })

        if self.status == 'Attended':
            if not self.class_representative:
                raise ValidationError({
                    'class_representative': "CUE Academic Audit Rule: Cannot log a lecture instance as 'Attended' "
                                            "without assigning a verifying Student representative code."
                })
            if not self.student_confirmed_at:
                from django.utils import timezone
                self.student_confirmed_at = timezone.now()

        if self.status == 'Rescheduled':
            if not self.rescheduled_by or not self.reschedule_requested_by_role:
                raise ValidationError({
                    'rescheduled_by': "Please document the user and requesting role initiating this reschedule event."
                })
            if not self.rescheduled_to_date or not self.rescheduled_to_time_slot or not self.rescheduled_to_venue:
                raise ValidationError({
                    'rescheduled_to_date': "You must complete all target fields (Date, Time, and Venue) when moving a class."
                })
            if (self.calendar_date == self.rescheduled_to_date and
                self.timetable_slot.time_slot == self.rescheduled_to_time_slot and
                    self.timetable_slot.venue == self.rescheduled_to_venue):
                raise ValidationError(
                    "Invalid Reschedule: Target coordinates match the original slot parameters.")

    def __str__(self):
        who = f" ({self.lecturer_assignment.lecturer})" if self.lecturer_assignment_id else ""
        return f"{self.calendar_date} : {self.timetable_slot.curriculum.course.course_code}{who} -> [{self.get_status_display()}]"


class DailyClassExecutionVenue(BaseModelMixin):
    """
    One-off venue change for a single class within a shared
    DailyClassExecution, on this specific date only — e.g. one class's
    usual room is unavailable today, but the rest of the cohort meets as
    normal. Distinct from a full 'Rescheduled' status, which moves the
    entire slot (every attending class) to a new date/time/venue.
    """
    execution = models.ForeignKey(
        'DailyClassExecution',
        on_delete=models.CASCADE,
        related_name='class_venues'
    )

    class_link = models.ForeignKey(
        'CurriculumClass',
        on_delete=models.CASCADE,
        related_name='daily_venue_overrides'
    )

    venue = models.ForeignKey(
        'Venue',
        on_delete=models.PROTECT,
        related_name='daily_execution_overrides'
    )

    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('execution', 'class_link')
        verbose_name = "Daily Execution Class Venue Override"

    def clean(self):
        super().clean()
        if self.class_link_id and self.execution_id:
            if self.class_link.curriculum_id != self.execution.timetable_slot.curriculum_id:
                raise ValidationError({
                    'class_link': "This class isn't attached to the curriculum this "
                    "execution's timetable slot belongs to."
                })

    def __str__(self):
        return f"{self.execution} — {self.class_link.Tclass.class_name} → {self.venue.venue_name}"
