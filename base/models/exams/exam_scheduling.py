# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
Exam scheduling domain — when and where each course's exam sits
(ExamSession), which physical space and invigilator squad covers it
(ExamVenue, ExamInvigilatorAssignment), and the timetable conflicts
that fall out of that scheduling (ExamClash).

Distinct from scheduling.Timetable: an ExamSession is a one-off sitting
tied to a Curriculum's exam period, not a recurring weekly slot. Both
domains depend on facilities.Venue for the physical space, which is why
Venue lives in its own subpackage rather than either one.

ExamSession.detect_all_clashes() needs a real Student import (not a
string FK) because it queries `Student.objects` directly rather than
just declaring a relation — everything else in this module references
Student only via string FKs on other models.
"""

from django.db import models
from django.core.exceptions import ValidationError

from ..base import BaseModelMixin
from ..student import Student


class ExamSession(BaseModelMixin):
    """A single exam sitting."""

    # TODO : move this to settings.py
    TIME_SLOTS = [
        ('08:00-11:00', '1st Slot (08:00 – 11:00)'),
        ('11:00-14:00', '2nd Slot (11:00 – 14:00)'),
        ('14:00-17:00', '3rd Slot (14:00 – 17:00)'),
        ('17:00-20:00', '4th Slot (17:00 – 20:00)'),
        ('20:00-23:00', '5th Slot (20:00 – 23:00)'),
    ]

    TYPE_CHOICES = [
        ('CAT',  'CAT'),
        ('MAIN', 'Main Exam'),
        ('SUPP', 'Supplementary'),
        ('SPECIAL', 'Special / Supplementary'),
        ('PRACTICAL', 'Practical'),
    ]

    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        related_name='exam_sessions'
    )  # when generating timetable common unit should be a concern here ,should be unique or not consider supp or unique together with type

    exam_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )
    date = models.DateField(null=True)
    time_slot = models.CharField(
        max_length=11,
        choices=TIME_SLOTS,
        null=True
    )

    class Meta:
        # one exam type per curriculum entry (course+class+session)
        unique_together = ('curriculum', 'exam_type')

    def __str__(self):
        return (
            f"{self.curriculum.course.course_code}"
            f" - {self.exam_type}"
            f" - {self.curriculum.session}"
        )

    @property
    def slot_start(self):
        """Returns '08:00' from '08:00-11:00'"""
        return self.time_slot.split('-')[0]

    @property
    def slot_end(self):
        """Returns '11:00' from '08:00-11:00'"""
        return self.time_slot.split('-')[1]

    @classmethod
    def detect_clashes_for_student(cls, student, session):
        """Find all exam time conflicts for a student in a session."""
        enrollments = student.enrollment_records.filter(
            curriculum__session=session,
            status='approved'
        ).values_list('curriculum_id', flat=True)

        exam_sessions = cls.objects.filter(
            curriculum_id__in=enrollments
        ).order_by('date', 'time_slot')

        clashes = []
        exam_list = list(exam_sessions)

        for i, exam_a in enumerate(exam_list):
            for exam_b in exam_list[i+1:]:
                # same date + same time_slot = clash
                if exam_a.date == exam_b.date and exam_a.time_slot == exam_b.time_slot:
                    clashes.append((exam_a, exam_b))

        return clashes

    @classmethod
    def detect_all_clashes(cls, session):
        """Run clash detection for all students in a session."""
        students = Student.objects.filter(
            enrollment_records__curriculum__session=session,
            enrollment_records__status='approved'
        ).distinct()

        for student in students:
            clashes = cls.detect_clashes_for_student(student, session)
            for exam_a, exam_b in clashes:
                ExamClash.objects.get_or_create(
                    student=student,
                    session_a=exam_a,
                    session_b=exam_b
                )


INVIGILATOR_ROLE_CHOICES = [
    ('Chief', 'Chief Invigilator (Room Lead)'),
    ('Assistant', 'Assistant Invigilator'),
    ('Relief', 'Relief / Floating Invigilator'),
]


class ExamVenue(BaseModelMixin):
    """
    Maps a specific physical space to an exam session slot.
    Supports a scalable squad of invigilators via an explicit through-table.
    """
    exam_session = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='venues'
    )

    venue = models.ForeignKey(
        'Venue',
        on_delete=models.PROTECT,
        related_name='exam_venues'
    )

    invigilators = models.ManyToManyField(
        'Lecturer',
        through='ExamInvigilatorAssignment',
        related_name='assigned_exam_venues',
        blank=True
    )

    class Meta:
        unique_together = ('exam_session', 'venue')
        verbose_name = "Exam Venue Slot"
        verbose_name_plural = "Exam Venue Slots"

    def __str__(self):
        return f"{self.exam_session} at {self.venue}"


# --- ADDED STATUS CHOICES ---
INVIGILATOR_ASSIGNMENT_STATUS_CHOICES = [
    ('Draft', 'Draft Assignment (Internal Planning)'),
    ('Published', 'Published / Notified (Lecturer Alerted)'),
    ('Confirmed', 'Confirmed / Accepted by Lecturer'),
    ('Excused', 'Excused / Absent with Apology'),
    ('Present', 'Present / Duty Executed (Exam Day Checked)'),
    ('Absent', 'Absent Without Apology (Flagged for HR review)'),
]


class ExamInvigilatorAssignment(BaseModelMixin):
    """
    Intermediary through-table linking lecturers to an ExamVenue slot.
    Tracks duty scheduling states, structural hierarchy, and attendance compliance.
    """
    exam_venue = models.ForeignKey(
        'ExamVenue',
        on_delete=models.CASCADE,
        related_name='invigilator_assignments'
    )

    lecturer = models.ForeignKey(
        'Lecturer',
        on_delete=models.PROTECT,
        related_name='exam_assignments'
    )

    role = models.CharField(
        max_length=20,
        choices=INVIGILATOR_ROLE_CHOICES,
        default='Assistant'
    )

    status = models.CharField(
        max_length=20,
        choices=INVIGILATOR_ASSIGNMENT_STATUS_CHOICES,
        default='Draft',
        db_index=True,
        help_text="Tracks the scheduling lifecycle and actual attendance on exam day."
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam_venue', 'lecturer')
        verbose_name = "Exam Invigilating Duty"
        verbose_name_plural = "Exam Invigilating Duties"

    def clean(self):
        """
        Operational Guardrails: Checks calendar collisions, status exceptions, 
        and leadership conflicts before saving.
        """
        super().clean()

        if self.exam_venue_id and self.lecturer_id:
            session = self.exam_venue.exam_session

            # 1. Smart Calendar Conflict Engine
            # Bugfix/Optimization: Only check for double-booking clashes if the assignment
            # is active ('Draft', 'Published', 'Confirmed', 'Present').
            # If the lecturer is 'Excused' or 'Absent', they are no longer occupying that time slot,
            # allowing the system to schedule a replacement lecturer without errors.
            active_statuses = ['Draft', 'Published', 'Confirmed', 'Present']

            if self.status in active_statuses:
                clash = ExamInvigilatorAssignment.objects.filter(
                    lecturer=self.lecturer,
                    exam_venue__exam_session__date=session.date,
                    exam_venue__exam_session__time_slot=session.time_slot,
                    status__in=active_statuses
                ).exclude(pk=self.pk)

                if clash.exists():
                    raise ValidationError({
                        'lecturer': f"Scheduling Clash: {self.lecturer} is already active "
                        f"at room '{clash.first().exam_venue.venue}' during this time block."
                    })

            # 2. Chief Leader Constraint Gatekeeper
            if self.role == 'Chief' and self.status in active_statuses:
                clashing_chiefs = ExamInvigilatorAssignment.objects.filter(
                    exam_venue=self.exam_venue,
                    role='Chief',
                    status__in=active_statuses
                ).exclude(pk=self.pk)

                if clashing_chiefs.exists():
                    raise ValidationError({
                        'role': f"Leadership Conflict: '{self.exam_venue.venue}' already has an active Chief Invigilator. "
                        f"Please register subsequent staff as Assistants."
                    })

    def __str__(self):
        return f"{self.lecturer} ({self.role}) - [{self.get_status_display()}]"


class ExamClash(BaseModelMixin):
    """Records detected exam clashes for a student."""

    # consider this when checking for student retakes and how to deal with that
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='exam_clashes'
    )

    session_a = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='clashes_a'
    )

    session_b = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='clashes_b'
    )

    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Clash for {self.student} — {self.session_a} vs {self.session_b}"
