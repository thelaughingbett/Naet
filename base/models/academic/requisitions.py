# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

"""
AcademicRequisition — resit, supplementary exam, missing-marks
investigation, and special/sit-in exam requests.

Deliberately NOT modeled on Complaint. A results *challenge* is
adversarial (the student disputes a decision someone made) and belongs
on Complaint's category='Results' / multi-level escalation ladder. A
resit request isn't a dispute against anyone — it's a normal academic
process with a linear two-stage sign-off (HOD recommends, Registrar
Academic Affairs approves) and often a fee gate before the student can
actually sit the exam. Forcing that through Complaint's SLA/escalation
machinery would be the wrong shape for it.
"""

import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin

REQUISITION_TYPE_CHOICES = [
    ('resit',          'Resit Examination'),
    ('supplementary',  'Supplementary Examination'),
    ('missing_marks',  'Missing / Unpublished Marks Investigation'),
    ('special_exam',   'Special Sit-in Exam (Missed for Valid Reason)'),
]

REQUISITION_STATUS_CHOICES = [
    ('pending',       'Pending Review'),
    ('hod_approved',  'Recommended by HOD — Awaiting Registrar'),
    ('approved',      'Approved'),
    ('rejected',      'Rejected'),
    ('completed',     'Completed'),
]

# Duplicated from ComplaintDocument.clean() rather than imported. Once a
# third document-attaching model shows up, pull both into a shared
# SupportingDocument abstract base — not worth the indirection for two.
ALLOWED_SUPPORTING_DOC_EXTENSIONS = [
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.heic', '.doc', '.docx',
]

OPEN_STATUSES = ['pending', 'hod_approved', 'approved']


class AcademicRequisition(BaseModelMixin):
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='requisitions'
    )

    enrollment = models.ForeignKey(
        'Enrollment',
        on_delete=models.PROTECT,
        related_name='requisitions',
        help_text="The unit registration this request concerns."
    )

    type = models.CharField(max_length=20, choices=REQUISITION_TYPE_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=REQUISITION_STATUS_CHOICES,
        default='pending'
    )

    reason = models.TextField(help_text="Why you're requesting this.")
    requested_at = models.DateTimeField(auto_now_add=True)

    # --- stage 1: HOD recommendation ---
    hod_reviewed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hod_reviewed_requisitions'
    )
    hod_reviewed_at = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True, null=True)

    # --- stage 2: Registrar Academic Affairs final decision ---
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requisitions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    registrar_remarks = models.TextField(blank=True, null=True)

    # --- fee gate ---
    # Resit/supplementary typically carry a fee; missing-marks and
    # special-exam requests generally don't. No fee-schedule model exists
    # yet, so fee_amount is set manually at review time rather than
    # looked up — flag this as a TODO once a rate table exists.
    fee_required = models.BooleanField(default=True)
    fee_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    fee_paid = models.BooleanField(default=False)
    fee_paid_at = models.DateTimeField(null=True, blank=True)

    # --- scheduling (set once approved, by the exams office) ---
    scheduled_date = models.DateField(null=True, blank=True)
    # Free text rather than Timetable.TIME_SLOTS to avoid a cross-app
    # import here — worth tightening to a shared choices list once the
    # exams office UI for this exists.
    scheduled_time_slot = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='e.g. "08:00-11:00"'
    )
    scheduled_venue = models.ForeignKey(
        'Venue',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Academic Requisition"
        verbose_name_plural = "Academic Requisitions"
        ordering = ['-requested_at']

    def clean(self):
        super().clean()

        if not self.enrollment_id:
            raise ValidationError({
                'enrollment': "A requisition must reference the unit registration it concerns."
            })
        if self.enrollment.student_id != self.student_id:
            raise ValidationError({
                'enrollment': "You can only file a requisition against your own enrollment."
            })

        # One open request per (student, enrollment, type) — otherwise a
        # frustrated double-click creates duplicate requests that get
        # reviewed independently and can end up with conflicting outcomes.
        if self._state.adding:
            dup = AcademicRequisition.objects.filter(
                student=self.student,
                enrollment=self.enrollment,
                type=self.type,
                status__in=OPEN_STATUSES,
            ).exists()
            if dup:
                raise ValidationError(
                    "You already have an open request of this type for this unit."
                )

        if self.status == 'rejected' and not (self.hod_remarks or self.registrar_remarks):
            raise ValidationError({
                'status': "A rejection must include a remark explaining why."
            })

        if self.fee_required and self.status in ('approved', 'completed') and self.fee_amount is None:
            raise ValidationError({
                'fee_amount': "An approved requisition requiring a fee must have the fee amount set."
            })

        if self.status == 'completed' and self.fee_required and not self.fee_paid:
            raise ValidationError({
                'fee_paid': "The fee must be cleared before this requisition can be marked completed."
            })

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'completed':
            self.completed_at = None

        if self.fee_paid and not self.fee_paid_at:
            self.fee_paid_at = timezone.now()
        elif not self.fee_paid:
            self.fee_paid_at = None

        super().save(*args, **kwargs)

    # --- workflow methods (mirrors the escalate() pattern on Complaint —
    #     mutate + full_clean() + save() through one call, rather than
    #     leaving callers to set fields directly and forget one) ---

    def hod_recommend(self, by_user, approve, remarks=""):
        if self.status != 'pending':
            raise ValidationError(
                "Only a pending requisition can receive an HOD recommendation."
            )
        self.hod_reviewed_by = by_user
        self.hod_reviewed_at = timezone.now()
        self.hod_remarks = remarks
        self.status = 'hod_approved' if approve else 'rejected'
        self.full_clean()
        self.save()

    def registrar_decide(self, by_user, approve, remarks="", fee_amount=None):
        if self.status != 'hod_approved':
            raise ValidationError(
                "A requisition can only receive a final decision after HOD recommendation."
            )
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.registrar_remarks = remarks
        if fee_amount is not None:
            self.fee_amount = fee_amount
        self.status = 'approved' if approve else 'rejected'
        self.full_clean()
        self.save()

    def schedule(self, date, time_slot, venue=None):
        if self.status != 'approved':
            raise ValidationError(
                "Only an approved requisition can be scheduled."
            )
        self.scheduled_date = date
        self.scheduled_time_slot = time_slot
        self.scheduled_venue = venue
        self.full_clean()
        self.save()

    def mark_completed(self):
        if self.status != 'approved':
            raise ValidationError(
                "Only an approved requisition can be marked completed.")
        if self.fee_required and not self.fee_paid:
            raise ValidationError(
                "Outstanding fee must be cleared before this requisition can be completed.")
        self.status = 'completed'
        self.full_clean()
        self.save()

    def __str__(self):
        course = self.enrollment.curriculum.course
        return f"[{self.get_type_display()}] {course.course_code} ({self.get_status_display()})"


class RequisitionDocument(BaseModelMixin):
    requisition = models.ForeignKey(
        'AcademicRequisition',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file = models.FileField(upload_to='requisitions/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_by_user = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='uploaded_requisition_docs'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.file:
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext not in ALLOWED_SUPPORTING_DOC_EXTENSIONS:
                raise ValidationError(
                    f"Unsupported file format '{ext}'. Allowed: "
                    f"{', '.join(ALLOWED_SUPPORTING_DOC_EXTENSIONS)}."
                )

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name
