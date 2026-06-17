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

from base.managers import CommonUnitCurriculumManager
from .base import BaseModelMixin
from simple_history.models import HistoricalRecords

from django.db import models


class Curriculum(BaseModelMixin):

    Tclass = models.ForeignKey(
        'Tclass',
        on_delete=models.PROTECT
    )

    course = models.ForeignKey(
        'Course',
        on_delete=models.PROTECT
    )

    professor = models.ManyToManyField(
        'Lecturer',
        blank=True,
    )

    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name="curricula"
    )

    results = models.ManyToManyField(
        "Student",
        through='Result'
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('course', 'Tclass', 'session')

    def __str__(self):
        return f"{self.course} - {self.session}"

    @classmethod
    def clone_curriculum(cls, from_session_id, to_session_id):
        source = cls.objects.filter(
            session_id=from_session_id
        ).prefetch_related('professor')

        professor_map = {}  # {(course_id, tclass_id): [professors]}

        new_records = []
        for req in source:
            obj = cls(
                course=req.course,
                Tclass=req.Tclass,
                session_id=to_session_id,
            )
            new_records.append(obj)
            professor_map[(req.course_id, req.Tclass_id)
                          ] = list(req.professor.all())

        cls.objects.bulk_create(new_records, ignore_conflicts=True)

        created = cls.objects.filter(
            session_id=to_session_id,
            course_id__in=[r.course_id for r in new_records],
            Tclass_id__in=[r.Tclass_id for r in new_records],
        )

        for obj in created:
            professors = professor_map.get((obj.course_id, obj.Tclass_id), [])
            if professors:
                obj.professor.set(professors)

        return created.count()


class CommonUnitCurriculum(Curriculum):

    objects = CommonUnitCurriculumManager()

    class Meta:
        proxy = True
        verbose_name = 'Common Unit'
        verbose_name_plural = 'Common Units'

    @property
    def classes(self):
        # find all curriculum entries for this course + session
        return Curriculum.objects.filter(
            course=self.course,
            session=self.session,
            course__type='CC'
        ).values_list('Tclass__class_name', flat=True)


class Enrollment(BaseModelMixin):

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )

    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.PROTECT,
        related_name='enrollment_records'
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending'
    )  # TODO : add  approved by,approved when

    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'curriculum')

    def __str__(self):
        return f"{self.student} → {self.curriculum} [{self.status}]"


class Result(BaseModelMixin):
    type_result = [
        ('C', 'Cat'),
        ('E', 'Exams')
    ]

    curricula = models.ForeignKey(
        'Curriculum',  # TODO : make sure only ones the student is enrolled is written
        on_delete=models.PROTECT
    )

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT
    )

    type = models.CharField(
        choices=type_result,
        default='C',
        max_length=45
    )

    score = models.DecimalField(
        decimal_places=2,
        max_digits=5
    )

    title = models.CharField(
        max_length=124
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.student} - {self.curricula} - {self.title}"
