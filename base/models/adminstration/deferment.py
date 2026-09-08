# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.db import models
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


class DefermentDocument(BaseModelMixin):
    """
    Supporting document uploaded alongside a deferment request.
    One deferment can have multiple attachments.
    """
    deferment = models.ForeignKey(
        'Deferment',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='deferments/%Y/%m/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    uploaded_by_user = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='uploaded_deferment_docs',
        null=True  # TODO :  remove this
    )

    def __str__(self):
        return f"{self.original_name} → {self.deferment}"


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
        ('requested', 'Requested'),
        ('active',      'Active'),
        ('reinstated',  'Reinstated'),
        ('withdrawn',   'Withdrawn'),
    ]

    # Approval workflow — separate from the deferment status itself
    REQUEST_STATUS_CHOICES = [
        ('pending',   'Pending Review'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
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
        help_text='Free text from student or registrar'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='requested'
    )
    request_status = models.CharField(
        max_length=10,
        choices=REQUEST_STATUS_CHOICES,
        default='pending'
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='approved_deferments',
        null=True,
        blank=True,
    )
    reinstated_at = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    def approve(self):
        pass

    def reject(self):
        pass

    def reinstate(self):
        pass

    def withdraw(self):
        pass

    class Meta:
        unique_together = ('student', 'session_deferred')

    def __str__(self):
        return f"{self.student} — deferred {self.session_deferred}"
