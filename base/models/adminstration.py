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

from simple_history.models import HistoricalRecords


class Deferment(BaseModelMixin):
    """
    Records each individual deferment event for a student.
    A student may defer multiple times — each gets its own record.
    """

    REASON_CHOICES = [
        ('financial',   'Financial Difficulty'),
        ('medical',     'Medical'),
        ('personal',    'Personal'),
        ('academic',    'Academic'),
        ('other',       'Other'),
    ]

    STATUS_CHOICES = [
        ('active',      'Active'),       # currently deferred
        ('reinstated',  'Reinstated'),   # came back
        ('withdrawn',   'Withdrawn'),    # did not return
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='deferments'
    )

    session_deferred = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='deferments',
        help_text='The session the student deferred from'
    )

    session_returning = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='returning_students',
        null=True,
        blank=True,
        help_text='The session the student is expected to return'
    )

    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='personal'
    )

    reason_detail = models.TextField(
        null=True,
        blank=True,
        help_text='Free text — additional context from registrar'
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='approved_deferments',
        null=True
    )

    history = HistoricalRecords()

    reinstated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # can't defer twice in the same session
        unique_together = ('student', 'session_deferred')

    def __str__(self):
        return f"{self.student} — deferred {self.session_deferred}"


class Reporting(BaseModelMixin):

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='reportings',
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name='reportings'
    )

    REPORTED_VIA_CHOICES = [
        ("online", "Online"),
        ("physical", "Physical")
    ]

    reported_at = models.DateTimeField(
        auto_now_add=True
    )

    reported_via = models.CharField(
        max_length=10,
        choices=REPORTED_VIA_CHOICES
    )

    history = HistoricalRecords()

    class Meta:
        # can't report twice in same session
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student} - {self.session}"
