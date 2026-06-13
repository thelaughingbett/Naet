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

from .student import Student


class Timetable(BaseModelMixin):

    session = models.ForeignKey("Session", on_delete=models.PROTECT)
    tclass = models.ForeignKey("Tclass", on_delete=models.PROTECT)
    course = models.ForeignKey("Course", on_delete=models.PROTECT)
    lecturer = models.ForeignKey("Lecturer", on_delete=models.PROTECT)
    DAY_CHOICES = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=100)

    class Meta:
        # prevent double-booking a venue or lecturer
        unique_together = [
            ('session', 'venue', 'day', 'start_time'),
            ('session', 'lecturer', 'day', 'start_time'),
        ]


class ExamSession(BaseModelMixin):
    """A single exam sitting"""

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name='exam_sessions'
    )

    course = models.ForeignKey(
        "Course",
        on_delete=models.PROTECT,
        related_name='exam_sessions'
    )

    TYPE_CHOICES = [
        ('CAT', 'CAT'),
        ('MAIN', 'Main Exam'),
        ('SUPP', 'Supplementary')
    ]

    exam_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        # same course can't have two main exams in same session
        unique_together = ('session', 'course', 'exam_type')

    @classmethod
    def detect_clashes_for_student(cls, student, session):
        """Find all exam time conflicts for a student in a session"""

        # get all courses this student is enrolled in
        enrolled_courses = student.enrollments.filter(
            session=session
        ).values_list('course_id', flat=True)

        # get all exam sessions for those courses
        exam_sessions = cls.objects.filter(
            session=session,
            course_id__in=enrolled_courses
        ).order_by('date', 'start_time')

        clashes = []
        exam_list = list(exam_sessions)

        for i, exam_a in enumerate(exam_list):
            for exam_b in exam_list[i+1:]:
                if exam_a.date == exam_b.date:
                    # check time overlap
                    if exam_a.start_time < exam_b.end_time and exam_a.end_time > exam_b.start_time:
                        clashes.append((exam_a, exam_b))

        return clashes

    @classmethod
    def detect_all_clashes(cls, session):
        """Run clash detection for all students in a session"""

        students = Student.objects.filter(
            enrollments__session=session
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
    """Which classes sit where for an exam"""

    exam_session = models.ForeignKey(
        "ExamSession",
        on_delete=models.PROTECT,
        related_name='venues'
    )

    tclass = models.ForeignKey(
        "Tclass",
        on_delete=models.PROTECT,
        related_name='exam_venues'
    )

    venue = models.CharField(max_length=100)

    invigilator = models.ForeignKey(
        "Lecturer",
        on_delete=models.PROTECT,
        related_name='invigilation_duties'
    )

    capacity = models.IntegerField()

    class Meta:
        # one venue, one time slot — no double booking
        unique_together = ('exam_session', 'venue')

    def clean(self):
        from django.core.exceptions import ValidationError

        # check invigilator not already assigned at this time
        clash = ExamVenue.objects.filter(
            invigilator=self.invigilator,
            exam_session__date=self.exam_session.date,
            exam_session__start_time=self.exam_session.start_time
        ).exclude(record_id=self.record_id)

        if clash.exists():
            raise ValidationError({
                'invigilator': f'{self.invigilator} is already assigned to another venue at this time'
            })

        super.clean(self)


class ExamClash(BaseModelMixin):
    """Records detected clashes for a student"""

    student = models.ForeignKey(
        "Student",
        on_delete=models.PROTECT,
        related_name='exam_clashes'
    )

    session_a = models.ForeignKey(
        "ExamSession",
        on_delete=models.PROTECT,
        related_name='clashes_a'
    )

    session_b = models.ForeignKey(
        "ExamSession",
        on_delete=models.PROTECT,
        related_name='clashes_b'
    )

    resolved = models.BooleanField(default=False)
