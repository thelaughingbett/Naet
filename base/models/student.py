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

import datetime

from django.db import models

from .base import (
    BaseModelMixin,
    hasUserMixin,
    id_type_choices,
)
from ..managers import (
    DeferredStudentManager,
    GraduatedStudentManager,
    ResidentStudentManager,

)

from .academic import Session


class Student(BaseModelMixin, hasUserMixin):
    MARRIAGE_STATUS = [
        ("M", "Married"),
        ("U", "Unmarried"),
    ]

    stay_choices = [
        ('resident', 'Resident'),
        ('outside',  'Outside'),
    ]

    # --- personal info ---
    marital_status = models.CharField(
        max_length=20, choices=MARRIAGE_STATUS, default="U")
    name_of_spouse = models.CharField(max_length=255, null=True, blank=True)
    spouse_contact = models.CharField(max_length=19, null=True, blank=True)
    occupation_of_spouse = models.CharField(
        max_length=255, null=True, blank=True)
    number_of_children = models.IntegerField(null=True, blank=True)

    id_type = models.CharField(
        max_length=24, default='national', choices=id_type_choices)
    national_id = models.CharField(
        max_length=34, default="xxxxxxx", unique=True)

    religion = models.CharField(max_length=34, default='pagan')
    nationality = models.CharField(max_length=34, default='Kenyan')
    ethnicity = models.CharField(max_length=34, default=' ')
    date_of_birth = models.DateField(default=datetime.date(2000, 4, 12))
    place_of_birth = models.CharField(max_length=255, default='')
    telephone_no = models.CharField(max_length=78, default='07xxxxx')
    school_email = models.EmailField(default='example@inst.com', unique=True)

    domicile = models.CharField(max_length=78, default='kenya')
    county = models.CharField(max_length=78, default='kenya')
    sub_county = models.CharField(max_length=78, default='kenya')
    constituency = models.CharField(max_length=78, default='kenya')
    division = models.CharField(max_length=78, default='')
    location = models.CharField(max_length=78, default='kenya')
    home_adress = models.CharField(max_length=78, default='kenya')

    # --- educational info ---
    registration_number = models.CharField(
        max_length=78, default='programme/000/2X', unique=True)

    class_entered = models.ForeignKey('Tclass', on_delete=models.PROTECT)

    stay = models.CharField(
        max_length=78, default='resident', choices=stay_choices)

    enrolled = models.DateTimeField(auto_now_add=True)
    deferred = models.BooleanField(default=False)

    name_of_secondary_school = models.CharField(max_length=78)
    address_of_secondary_school = models.CharField(max_length=255)

    enrollments = models.ManyToManyField(
        'Curriculum',
        related_name='enrolled_students',
        through='Enrollment',
        blank=True
    )

    def __str__(self):
        return self.registration_number

    @property
    def expected_graduation_session(self):
        PROGRAMME_SEMESTERS = 8

        deferred_count = self.deferments.exclude(status='withdrawn').count()
        total_semesters = PROGRAMME_SEMESTERS + deferred_count

        try:

            all_sessions = list(
                Session.objects.order_by('academic_year', 'semester')
                .values('record_id', 'academic_year', 'semester')
            )

            enrollment_session = Session.objects.filter(
                curriculum__enrollment_records__student=self,
            ).order_by('academic_year', 'semester').first()

            if not enrollment_session:
                return None

            start_idx = next(
                (i for i, s in enumerate(all_sessions)
                 if str(s['record_id']) == str(enrollment_session.record_id)),
                None
            )

            if start_idx is None:
                return None

            grad_idx = start_idx + total_semesters - 1
            if grad_idx >= len(all_sessions):
                return None

            grad_session_id = all_sessions[grad_idx]['record_id']
            return Session.objects.get(record_id=grad_session_id)

        except Exception:
            return None

    @property
    def semesters_remaining(self):
        from .academic import Session

        expected = self.expected_graduation_session
        current = Session.objects.filter(is_active=True).first()

        if not expected or not current:
            return None

        all_sessions = list(
            Session.objects.order_by('academic_year', 'semester')
            .values_list('record_id', flat=True)
        )

        try:
            current_idx = [str(s) for s in all_sessions].index(
                str(current.record_id))
            expected_idx = [str(s) for s in all_sessions].index(
                str(expected.record_id))
            return max(expected_idx - current_idx, 0)
        except ValueError:
            return None

    @property
    def is_overdue(self):
        if self.class_entered.graduated:
            return False
        remaining = self.semesters_remaining
        return remaining is not None and remaining < 0

    @property
    def current_hostel(self):
        from .academic import Session
        session = Session.objects.filter(is_active=True).first()
        if not session:
            return None
        allocation = self.hostel_allocations.filter(
            session=session, is_active=True
        ).select_related('room__hostel').first()
        return allocation.room if allocation else None


class DeferredStudent(Student):
    """Proxy — deferred students only, separate admin view."""
    objects = DeferredStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Deferred Students'

    def reinstate(self):
        self.deferred = False
        self.save()

    @property
    def days_deferred(self):
        from django.utils import timezone
        return (timezone.now().date() - self.updated_at.date()).days


class ResidentStudent(Student):
    """Proxy — resident students only."""
    objects = ResidentStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Resident Students'


class GraduatedStudent(Student):
    """Proxy — graduated students only."""
    objects = GraduatedStudentManager()

    class Meta:
        proxy = True
        verbose_name_plural = 'Graduated Students'
