from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
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

    # --- HOD / registrar response -----------------------------------
    # Whoever actioned the request (approved or rejected), independent
    # of approved_by which historically only made sense for approvals.
    reviewed_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='reviewed_deferments',
        null=True,
        blank=True,
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    review_remarks = models.TextField(
        blank=True,
        default='',
        help_text="HOD/registrar's response to the request — reason for "
        "rejection, or conditions attached to an approval."
    )

    # --- printable confirmation ---------------------------------------
    confirmation_reference = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Generated once approved, e.g. 'DEF-2026-000123'. "
        "Printed on the confirmation document as the official reference."
    )

    confirmation_document = models.FileField(
        upload_to='deferments/confirmations/%Y/%m/',
        null=True,
        blank=True,
        help_text="Generated printable PDF confirming the deferment, "
        "produced once request_status='approved'."
    )

    reinstated_at = models.DateTimeField(
        null=True,
        blank=True
    )
    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'session_deferred')

    def __str__(self):
        return f"{self.student} — deferred {self.session_deferred}"

    def clean(self):
        super().clean()

        if self.request_status == 'rejected' and not self.review_remarks:
            raise ValidationError({
                'review_remarks': "A reason must be given when rejecting a deferment request."
            })

        if self.status == 'reinstated' and not self.reinstated_at:
            self.reinstated_at = timezone.now()

    def _generate_confirmation_reference(self):
        year = self.session_deferred.academic_year if hasattr(
            self.session_deferred, 'academic_year') else timezone.now().year
        return f"DEF-{year}-{self.pk:06d}"

    # --- workflow actions -----------------------------------------------

    def approve(self, by_user, remarks=""):
        if self.request_status != 'pending':
            raise ValidationError(
                "Only a pending request can be approved.")

        self.request_status = 'approved'
        self.status = 'active'
        self.approved_by = by_user
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.review_remarks = remarks
        self.full_clean()
        self.save()

        if not self.confirmation_reference:
            self.confirmation_reference = self._generate_confirmation_reference()
            self.save(update_fields=['confirmation_reference'])
        # Actual PDF rendering (confirmation_document) is generated
        # separately via a document-generation service/task, keyed off
        # confirmation_reference, then attached back to this field.

    def reject(self, by_user, remarks):
        if self.request_status != 'pending':
            raise ValidationError(
                "Only a pending request can be rejected.")
        if not remarks:
            raise ValidationError(
                "A rejection reason is required.")

        self.request_status = 'rejected'
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.review_remarks = remarks
        self.full_clean()
        self.save()

    def reinstate(self):
        if self.status != 'active':
            raise ValidationError(
                "Only an active deferment can be reinstated.")

        self.status = 'reinstated'
        self.reinstated_at = timezone.now()
        self.full_clean()
        self.save()

    def withdraw(self):
        if self.status not in ('requested', 'active'):
            raise ValidationError(
                "Only a requested or active deferment can be withdrawn.")

        self.status = 'withdrawn'
        self.full_clean()
        self.save()
