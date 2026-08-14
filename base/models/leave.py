"""
Leave Request system — staff leave application, approval, and balance
tracking. Applies to any staff member (Lecturer, AdministrativeStaff,
ItStaff, FinanceStaff, etc.) since leave isn't role-specific, so this hangs
off `User` rather than any one staff subtype.
"""
import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .base import BaseModelMixin, ValidatedFileMixin


class LeaveType(BaseModelMixin):
    """
    Configurable leave category, e.g. Annual, Sick, Maternity, Paternity,
    Study, Compassionate, Unpaid, Sabbatical, Duty/On-Duty. Kept as data
    (like GradeScale) rather than a hardcoded choices list, since
    entitlements and rules vary by institution and change over time.
    """

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    default_days_per_year = models.PositiveSmallIntegerField(
        default=21,
        help_text="Standard entitlement; overridable per staff member via LeaveBalance"
    )
    is_paid = models.BooleanField(default=True)
    requires_document = models.BooleanField(
        default=False,
        help_text="e.g. medical certificate for Sick leave"
    )
    requires_substitute_arrangement = models.BooleanField(
        default=True,
        help_text="Whether a covering colleague must be named — relevant for teaching staff",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LeaveBalance(BaseModelMixin):
    """
    A staff member's entitlement for one leave type in one calendar year.
    `days_used` is computed from approved LeaveRequests, not stored, so it
    can't drift out of sync — same pattern as StudentFeeAccount.amount_paid.
    """
    # TODO :  this is auto created every time a new user is added to the system and when academic year is progressed

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leave_balances"
    )

    leave_type = models.ForeignKey(
        'LeaveType',
        on_delete=models.PROTECT,
        related_name="balances"
    )

    # TODO :  change to charfield i.e 2025/2026
    year = models.PositiveIntegerField()
    # TODO : calculated from leave type hence to be changed to a property
    entitled_days = models.PositiveSmallIntegerField()
    carried_forward_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Unused days carried over from the previous year, if policy allows"
    )  # TODO :  also a property

    class Meta:
        unique_together = ("staff", "leave_type", "year")

    def __str__(self):
        return f"{self.staff} — {self.leave_type} ({self.year})"

    @property
    def days_used(self):
        """
        Sum of `number_of_days` across this staff member's approved,
        non-cancelled requests of this leave type that fall within this
        calendar year.
        """
        requests = LeaveRequest.objects.filter(
            applicant=self.staff,
            leave_type=self.leave_type,
            status=LeaveRequest.Status.APPROVED,
            start_date__year=self.year,
        )
        return sum(r.number_of_days for r in requests)

    @property
    def total_available_days(self):
        return self.entitled_days + self.carried_forward_days

    @property
    def days_remaining(self):
        return self.total_available_days - self.days_used


class LeaveRequest(BaseModelMixin):
    """
    A single leave application. Explicitly separates the *personal* leave
    status from the approval workflow status the way Deferment separates
    `status` from `request_status` — here it's one field, but the same
    "who's covering my duties while I'm away" concern from the HOD sidebar's
    Substitute/Duty Arrangement gets a real field rather than being buried
    in free-text `reason`.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled by Applicant"

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leave_requests"
    )
    leave_type = models.ForeignKey(
        'LeaveType',
        on_delete=models.PROTECT,
        related_name="requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    substitute_arrangement = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="covering_for_leave_requests",
        help_text="Colleague covering duties during this leave, if the leave type requires it",
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_leave_approvals",
        help_text="Whoever's turn it is in the approval chain right now — null once fully decided",
    )
    decided_at = models.DateTimeField(
        null=True,
        blank=True
    )
    decision_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.applicant} — {self.leave_type} ({self.start_date} to {self.end_date}) [{self.status}]"

    @property
    def name(self):
        if hasattr(self.applicant, 'lecturer_profile'):
            return self.applicant.lecturer_profile.name

    @property
    def number_of_days(self):
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        super().clean()

        if self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot be before the start date."})

        if self.leave_type_id and self.leave_type.requires_substitute_arrangement and not self.substitute_arrangement:
            raise ValidationError({
                "substitute_arrangement": f"{self.leave_type} requires naming a colleague to cover duties."
            })

        if self.status == self.Status.APPROVED:
            balance = LeaveBalance.objects.filter(
                staff=self.applicant,
                leave_type=self.leave_type,
                year=self.start_date.year
            ).first()
            if balance is None:
                raise ValidationError(
                    f"No {self.leave_type} balance configured for {self.applicant} in {self.start_date.year}."
                )
            # Exclude self when re-approving an already-approved request being edited
            already_used = balance.days_used - \
                (self.number_of_days if self.pk and self.status ==
                 self.Status.APPROVED else 0)
            if already_used + self.number_of_days > balance.total_available_days:
                raise ValidationError(
                    f"This request ({self.number_of_days} days) would exceed the remaining "
                    f"{self.leave_type} balance ({balance.days_remaining} days)."
                )

    def submit(self):
        """Move from Draft to Pending, kicking off the approval chain."""
        from django.utils import timezone
        self.status = self.Status.PENDING
        self.submitted_at = timezone.now()
        self.full_clean()
        self.save()

    def approve(self, by_user, remarks=""):
        from django.utils import timezone
        self.status = self.Status.APPROVED
        self.current_approver = None
        self.decided_at = timezone.now()
        self.decision_remarks = remarks
        self.full_clean()
        self.save()
        LeaveApprovalStep.objects.filter(
            leave_request=self,
            approver=by_user,
            status=LeaveApprovalStep.Status.PENDING
        ).update(
            status=LeaveApprovalStep.Status.APPROVED,
            decided_at=timezone.now(),
            remarks=remarks
        )

    def reject(self, by_user, remarks=""):
        from django.utils import timezone
        self.status = self.Status.REJECTED
        self.current_approver = None
        self.decided_at = timezone.now()
        self.decision_remarks = remarks
        self.save()
        LeaveApprovalStep.objects.filter(
            leave_request=self,
            approver=by_user,
            status=LeaveApprovalStep.Status.PENDING
        ).update(
            status=LeaveApprovalStep.Status.REJECTED,
            decided_at=timezone.now(),
            remarks=remarks
        )


class LeaveApprovalStep(BaseModelMixin):
    """
    One step in a (possibly multi-level) approval chain for a leave
    request — e.g. HOD, then Dean, then HR — same audit-trail reasoning as
    ComplaintEscalationHistory: each approver's decision is its own
    permanent row, not an overwritten status field.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SKIPPED = "skipped", "Skipped"

    leave_request = models.ForeignKey(
        'LeaveRequest',
        on_delete=models.CASCADE,
        related_name="approval_steps"
    )
    order = models.PositiveSmallIntegerField(
        help_text="1 = first approver in the chain, 2 = next, etc."
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ("leave_request", "order")
        ordering = ["order"]

    def __str__(self):
        return f"Step {self.order}: {self.approver} [{self.status}]"


class LeaveRequestDocument(ValidatedFileMixin, BaseModelMixin):
    """Supporting document — e.g. a medical certificate for Sick leave."""

    leave_request = models.ForeignKey(
        'LeaveRequest',
        on_delete=models.CASCADE,
        related_name="documents"
    )

    allowed_mime_types = {
        ".pdf": ["application/pdf"],
        ".png": ["image/png"],
        ".jpg": ["image/jpeg"],
        ".jpeg": ["image/jpeg"],
        ".doc": ["application/msword"],
        ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    }

    def __str__(self):
        return f"Doc for {self.leave_request}: {self.original_name}"
