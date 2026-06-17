# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .base import BaseModelMixin
from django.db import models
from base.models import Session
from .student import Student


class Timetable(BaseModelMixin):

    curriculum = models.ForeignKey(
        "Curriculum",
        on_delete=models.PROTECT,  # TODO : change this to curriculum ✔️
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

    TIME_SLOTS = [
        ('08:00-10:00', '1st Slot (08:00 - 10:00)'),
        ('10:00-12:00', '2nd Slot (10:00 - 12:00)'),
        ('12:00-13:00', '3rd Slot (12:00 - 13:00)'),
        ('13:00-15:00', '4th Slot (13:00 - 15:00)'),
        ('15:00-17:00', '5th Slot (15:00 - 17:00)'),
        ('17:00-19:00', '6th Slot (17:00 - 19:00)'),
    ]

    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    time_slot = models.CharField(max_length=11, choices=TIME_SLOTS)

    venue = models.ForeignKey(
        "Venue",
        on_delete=models.DO_NOTHING,
        related_name="timetable_slots"
    )

    class Meta:
        # prevent double-booking a venue or lecturer
        unique_together = [
            # ('curriculum__session', 'venue', 'day', 'start_time'),
            # ('curriculum_session', 'lecturer', 'day', 'start_time'),
        ]

    def __str__(self):
        return f"{self.curriculum}- {self.day}"


class ExamSession(BaseModelMixin):
    """A single exam sitting."""

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
    )

    exam_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date = models.DateField()
    time_slot = models.CharField(max_length=11, choices=TIME_SLOTS)

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


class ExamVenue(BaseModelMixin):
    """Which venue hosts an exam session, and who invigilates."""

    exam_session = models.ForeignKey(
        'ExamSession',
        on_delete=models.PROTECT,
        related_name='venues'
    )

    venue = models.ForeignKey(
        'Venue',
        on_delete=models.DO_NOTHING,
        related_name='exam_venues'
    )

    invigilator = models.ForeignKey(
        'Lecturer',
        on_delete=models.PROTECT,
        related_name='invigilation_duties'
    )

    class Meta:
        unique_together = ('exam_session', 'venue')

    def clean(self):
        from django.core.exceptions import ValidationError

        clash = ExamVenue.objects.filter(
            invigilator=self.invigilator,
            exam_session__date=self.exam_session.date,
            exam_session__time_slot=self.exam_session.time_slot,  # ← time_slot not start_time
        ).exclude(record_id=self.record_id)

        if clash.exists():
            raise ValidationError({
                'invigilator': (
                    f'{self.invigilator} is already assigned '
                    f'to another venue at this time'
                )
            })

        super().clean()  # ← fixed syntax

    def __str__(self):
        return f"{self.exam_session} — {self.venue} — {self.invigilator}"


class ExamClash(BaseModelMixin):
    """Records detected exam clashes for a student."""

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


class Venue(BaseModelMixin):
    capacity = models.IntegerField()
    venue_name = models.CharField(
        max_length=34,
        unique=True
    )

    def __str__(self):
        return f"{self.venue_name} - {self.capacity}"


class ExamCard(BaseModelMixin):
    """
    Represents an issued exam admit card for a student in a session.
    Serial number and QR payload are generated once and reused —
    regenerating creates a new ExamCard record (old one is superseded).

    A student can only have ONE active card per session.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='exam_cards'
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.PROTECT,
        related_name='exam_cards'
    )

    serial_number = models.CharField(max_length=30, unique=True)

    is_active = models.BooleanField(default=True)

    issued_at = models.DateTimeField(auto_now_add=True)
    last_printed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'session', 'is_active')
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.serial_number} — {self.student.registration_number} ({self.session})"

    @classmethod
    def generate_serial(cls):
        """UNI-2026-XXXX-XXXX format, guaranteed unique."""
        import random
        from datetime import datetime

        while True:
            year = datetime.now().year
            r1 = str(random.randint(0, 9999)).zfill(4)
            r2 = str(random.randint(0, 9999)).zfill(4)
            serial = f"UNI-{year}-{r1}-{r2}"
            if not cls.objects.filter(serial_number=serial).exists():
                return serial

    @property
    def qr_payload(self):
        """String encoded into the QR — verifiable at exam halls."""
        return f"{self.student.registration_number}|{self.serial_number}|{self.session}"
