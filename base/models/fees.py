# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from .base import BaseModelMixin


# ─────────────────────────────────────────────────────────────────────────────
# Core billing
# ─────────────────────────────────────────────────────────────────────────────

class FeeStructure(BaseModelMixin):
    """Defines what a class owes per session"""

    Tclass = models.ForeignKey(
        "Tclass",
        on_delete=models.PROTECT,
        related_name='fee_structures'
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name='fee_structures'
    )

    # breakdown e.g {"tuition": 45000, "registration": 5000, "hostel": 12000}
    breakdown = models.JSONField()

    @property
    def total_amount(self):
        total = 0
        for key in self.breakdown:
            total += self.breakdown[key]
        return total

    class Meta:
        unique_together = ('Tclass', 'session')

    def __str__(self):
        return f"{self.Tclass} - {self.session}"

    # TODO : add a method to copy past structure to next class during rollover


class StudentFeeAccount(BaseModelMixin):
    """Per-student ledger for a session"""

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,
        related_name='fee_accounts'
    )

    fee_structure = models.ForeignKey(
        'FeeStructure',
        on_delete=models.PROTECT
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'fee_structure')

    @property
    def amount_paid(self):
        """
        Gross sum of completed payments against this account. This is the
        only source of truth for how much has been paid in — there is no
        separate stored ledger value to keep in sync. Use `net_paid` if you
        want this figure net of refunds.
        """
        total = self.payments.filter(
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def amount_refunded(self):
        """Sum of completed refunds against this account."""
        total = self.refunds.filter(
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def net_paid(self):
        """What the student has effectively paid in, after refunds."""
        return self.amount_paid - self.amount_refunded

    @property
    def amount_charges(self):
        """
        Sum of active ad-hoc charges (fines, damages, supplementary exams,
        late penalties, etc.) layered on top of the base fee structure.
        """
        total = self.charges.filter(
            status='billed'
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def amount_scholarship(self):
        """Sum of disbursed scholarship/bursary coverage applied here."""
        total = self.scholarship_awards.filter(
            status='disbursed'
        ).aggregate(total=models.Sum('amount_covered'))['total']
        return total or Decimal('0.00')

    @property
    def amount_billed(self):
        """Base fee structure total plus any active ad-hoc charges."""
        return self.fee_structure.total_amount  # + self.amount_charges

    @property
    def balance(self):
        # Can go negative if the student has overpaid (or been over-covered
        # by a scholarship) — that's fine, a negative balance just reads
        # as a credit.
        return self.amount_billed - self.net_paid - self.amount_scholarship

    @property
    def available_credit(self):
        """Overpayment amount currently available to refund, if any."""
        return max(Decimal('0.00'), -self.balance)

    @property
    def is_cleared(self):
        return self.balance <= 0

    @property
    def days_remaining(self):
        # Subtracts today's date from the due date

        delta = self.fee_structure.session.end_date - \
            datetime.timedelta(days=14)
        return delta

    def __str__(self):
        return f"{self.student.registration_number} - {self.fee_structure} - balance: {self.balance}"


class Payment(BaseModelMixin):
    """Individual payment transactions"""

    STATUS_CHOICES = [
        ("pending",   "Pending"),    # initiated, awaiting confirmation
        ("completed", "Completed"),  # confirmed by webhook
        ("failed",    "Failed"),     # timed out or rejected
        ("cancelled", "Cancelled"),  # cancelled by student
    ]

    account = models.ForeignKey(
        'StudentFeeAccount',
        on_delete=models.PROTECT,
        related_name='payments'
    )

    PAYMENT_METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("bank", "Bank Transfer"),
        ("cash", "Cash"),
    ]  # change to derive from payment module

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES
    )

    transaction_ref = models.CharField(
        max_length=100,
        unique=True,
        null=True,    # null until confirmed by webhook
        blank=True
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # provider-specific metadata
    provider_ref = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )  # MerchantRequestID, CheckoutRequestID, bank ref

    phone_number = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )  # for M-Pesa STK push

    # Set when this payment was made by/via a third-party sponsor (a bank
    # transfer or cheque from a corporate/government sponsor, for example)
    # rather than the student directly. Distinct from ScholarshipAward,
    # which covers bill reduction that isn't routed through an actual
    # Payment (e.g. a capitation subsidy).
    sponsor = models.ForeignKey(
        'Sponsor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )

    paid_at = models.DateTimeField(auto_now_add=True)
    initiated_at = models.DateTimeField(auto_now_add=True)  # ???

    history = HistoricalRecords()

    class Meta:
        unique_together = ('transaction_ref', 'method')

    def __str__(self):
        return f"{self.account} - {self.transaction_ref}"

    def save(self, *args, **kwargs):
        if self._state.adding and self.account.is_cleared:
            raise ValidationError("This fee account has already been cleared.")
        super().save(*args, **kwargs)

    def confirm(self, transaction_ref, provider_ref=None):
        """
        Called by the webhook handler when payment is confirmed.
        Fires notifications. amount_paid/balance update automatically
        since they're derived from completed payments — nothing to
        write back to the account here.
        """
        from base.utils.signals import send_notification

        self.status = 'completed'
        self.transaction_ref = transaction_ref
        self.provider_ref = provider_ref
        self.paid_at = timezone.now()
        self.save()  # now safe — only checks is_cleared on creation, not here

        # fire notification
        send_notification.send(
            sender=self.__class__,
            user=self.account.student.user,
            template_key='payment_confirmed',
            channels=['sms', 'email'],
            context={
                'student_name': self.account.student.user.full_name,
                'amount':       self.amount,
                'method':       self.get_method_display(),
                'ref':          self.transaction_ref,
                'balance':      self.account.balance,
                'is_cleared':   self.account.is_cleared,
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# Ad-hoc charges
# ─────────────────────────────────────────────────────────────────────────────

class Charge(BaseModelMixin):
    """
    An ad-hoc amount billed to a student's fee account on top of the base
    FeeStructure — fines, damages, supplementary exam fees, ID replacement,
    late penalties, etc. Only 'billed' charges count toward the account's
    amount_billed (see StudentFeeAccount.amount_charges).
    """

    CATEGORY_CHOICES = [
        ("library_fine",       "Library Fine"),
        ("hostel_damage",      "Hostel / Property Damage"),
        ("supplementary_exam", "Supplementary Exam Fee"),
        ("exam_card_reprint",  "Exam Card Reprint"),
        ("id_replacement",     "ID Card Replacement"),
        ("transcript",         "Transcript / Document Fee"),
        ("late_fee",           "Late Payment Penalty"),
        ("disciplinary",       "Disciplinary Fine"),
        ("other",              "Other"),
    ]

    STATUS_CHOICES = [
        ("draft",    "Draft"),     # being prepared, not yet counted
        ("billed",   "Billed"),    # active, counts toward amount_billed
        ("waived",   "Waived"),    # forgiven — doesn't count
        ("reversed", "Reversed"),  # mistaken entry, corrected
    ]

    account = models.ForeignKey(
        'StudentFeeAccount',
        on_delete=models.PROTECT,
        related_name='charges',
    )  # ??? to be removed

    category = models.CharField(
        max_length=25,
        choices=CATEGORY_CHOICES,
        default='other',
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='billed',
        db_index=True,
    )

    waived_reason = models.CharField(max_length=255, blank=True, default="")

    charged_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges_issued',
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Fee Account Charge"
        verbose_name_plural = "Fee Account Charges"

    def __str__(self):
        return (f"{self.account.student.registration_number} — "
                f"{self.get_category_display()} — KES {self.amount} "
                f"[{self.get_status_display()}]")

    def clean(self):
        super().clean()
        if self.status == 'waived' and not self.waived_reason:
            raise ValidationError({
                'waived_reason': "A reason is required when waiving a charge."
            })

    def waive(self, reason, by_user=None):
        if self.status != 'billed':
            return
        self.status = 'waived'
        self.waived_reason = reason
        if by_user:
            self.charged_by = self.charged_by or by_user
        self.save()

    @classmethod
    def apply_late_fees(cls, session, applied_by=None):
        """
        Creates a 'late_fee' Charge for every account in `session` that:
          - has an active LateFeePolicy attached to its FeeStructure,
          - is not yet cleared,
          - is past that policy's grace period beyond the account's due date,
          - hasn't already been charged a late fee since that due date.

        Idempotent per due-date window — safe to run daily via a management
        command/cron rather than being triggered per-request.
        """
        created = []
        today = timezone.now().date()

        accounts = StudentFeeAccount.objects.filter(
            fee_structure__session=session
        ).select_related('fee_structure', 'fee_structure__late_fee_policy')

        for account in accounts:
            if account.is_cleared:
                continue

            policy = getattr(account.fee_structure, 'late_fee_policy', None)
            if not policy or not policy.is_active:
                continue

            due_date = account.days_remaining
            grace_deadline = due_date + \
                datetime.timedelta(days=policy.grace_period_days)
            if today <= grace_deadline:
                continue

            already_charged = account.charges.filter(
                category='late_fee', created_at__date__gte=due_date
            ).exists()
            if already_charged:
                continue

            if policy.penalty_type == 'fixed':
                amount = policy.penalty_amount
            else:
                amount = (
                    account.balance *
                    policy.penalty_percentage / Decimal('100')
                ).quantize(Decimal('0.01'))

            charge = cls.objects.create(
                account=account,
                category='late_fee',
                description=f"Late payment penalty ({policy.get_penalty_type_display()})",
                amount=amount,
                status='billed',
                charged_by=applied_by,
            )
            created.append(charge)

        return created


# ─────────────────────────────────────────────────────────────────────────────
# Refunds
# ─────────────────────────────────────────────────────────────────────────────

class Refund(BaseModelMixin):
    """
    Money returned to a student against their fee account — overpayments,
    withdrawal refunds, caution-money refunds at graduation/clearance, etc.

    Mirrors Payment's status lifecycle, but nets *against* net_paid rather
    than mutating any existing Payment record — a refund never edits or
    deletes the payment it's correcting, it's its own append-only entry.
    """

    REASON_CHOICES = [
        ('overpayment',       'Overpayment'),
        ('withdrawal',        'Withdrawal / Deferment Refund'),
        ('caution_money',     'Caution Money Refund'),
        ('duplicate_payment', 'Duplicate Payment Correction'),
        ('other',             'Other'),
    ]

    METHOD_CHOICES = Payment.PAYMENT_METHOD_CHOICES  # reuse the same set

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    account = models.ForeignKey(
        'StudentFeeAccount',
        on_delete=models.PROTECT,
        related_name='refunds',
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)

    transaction_ref = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    requested_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds_requested',
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds_approved',
    )  # set a policy to make sure user is set as reg staff number or historical records
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    notes = models.CharField(max_length=255, blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ('transaction_ref', 'method')
        ordering = ['-created_at']
        verbose_name = "Fee Refund"
        verbose_name_plural = "Fee Refunds"

    def __str__(self):
        return f"Refund — {self.account} — KES {self.amount} [{self.get_status_display()}]"

    def clean(self):
        super().clean()

        # Overpayment/duplicate-payment refunds shouldn't exceed the
        # account's actual credit. Caution-money and other discretionary
        # refunds are allowed to push the balance back up, since that
        # reflects money legitimately being returned (e.g. at clearance)
        # rather than correcting an accounting error.
        if (self.reason in ('overpayment', 'duplicate_payment')
                and self.account_id and self._state.adding):
            if self.amount > self.account.available_credit:
                raise ValidationError({
                    'amount': f"Refund exceeds the account's available credit "
                    f"(KES {self.account.available_credit})."
                })

    def approve(self, by_user):
        if self.status != 'pending':
            return
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def mark_completed(self, transaction_ref=None):
        if self.status not in ('pending', 'approved'):
            return
        self.status = 'completed'
        if transaction_ref:
            self.transaction_ref = transaction_ref
        self.processed_at = timezone.now()
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
# Sponsors & scholarships
# ─────────────────────────────────────────────────────────────────────────────

class Sponsor(BaseModelMixin):
    """A third party that pays or subsidises student fees."""

    SPONSOR_TYPE_CHOICES = [
        ('government',    'Government / HELB'),
        ('ngcdf',         'NG-CDF'),
        ('corporate',     'Corporate Sponsor'),
        ('religious',     'Religious Organization'),
        ('individual',    'Individual / Family Sponsor'),
        ('institutional', 'Institutional Scholarship Fund'),
        ('other',         'Other'),
    ]

    name = models.CharField(max_length=200, unique=True)
    sponsor_type = models.CharField(
        max_length=20,
        choices=SPONSOR_TYPE_CHOICES,
        default='other'
    )

    contact_person = models.CharField(max_length=150, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Sponsor"
        verbose_name_plural = "Sponsors"

    def __str__(self):
        return self.name

# TODO Add scholarship applicationn  with documents to support the application and student etc


class Scholarship(BaseModelMixin):
    """
    A named award/bursary programme run by a Sponsor — the offer itself,
    not any one student's outcome. Per-student awards are recorded via
    ScholarshipAward, which snapshots the actual KES amount at award time.
    """

    COVERAGE_TYPE_CHOICES = [
        ('full',               'Full Tuition Coverage'),
        ('partial_percentage', 'Partial — Percentage of Bill'),
        ('partial_fixed',      'Partial — Fixed Amount'),
        ('category_specific',  'Specific Fee Category Only'),
    ]

    sponsor = models.ForeignKey(
        'Sponsor',
        on_delete=models.PROTECT,
        related_name='scholarships'
    )

    name = models.CharField(max_length=200)
    coverage_type = models.CharField(
        max_length=20,
        choices=COVERAGE_TYPE_CHOICES
    )

    coverage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Used when coverage_type='partial_percentage'. e.g. 50.00 for 50%.",
    )
    coverage_amount = models.DecimalField(
        max_digits=10,
        null=True,
        blank=True,
        decimal_places=2,
        help_text="Fixed KES amount. Used when coverage_type is "
        "'partial_fixed' or 'category_specific'.",
    )
    covered_category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="",
        help_text="Matches a key in FeeStructure.breakdown, e.g. 'tuition'. "
        "Required when coverage_type='category_specific'.",
    )

    session = models.ForeignKey(
        'Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scholarships',
        help_text="Optional — restrict this award programme to one "
        "session's award cycle.",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sponsor', 'name']
        verbose_name = "Scholarship / Bursary Programme"
        verbose_name_plural = "Scholarship / Bursary Programmes"

    def __str__(self):
        return f"{self.name} ({self.sponsor.name})"

    def clean(self):
        super().clean()

        if self.coverage_type == 'partial_percentage' and self.coverage_percentage is None:
            raise ValidationError({
                'coverage_percentage': "Required for percentage-based coverage."
            })
        if self.coverage_type in ('partial_fixed', 'category_specific') and self.coverage_amount is None:
            raise ValidationError({
                'coverage_amount': "Required for fixed/category-specific coverage."
            })
        if self.coverage_type == 'category_specific' and not self.covered_category:
            raise ValidationError({
                'covered_category': "Required for category-specific coverage."
            })

    def compute_award_amount(self, account):
        """
        Given a StudentFeeAccount, compute what this scholarship would
        cover against it — used when creating a ScholarshipAward, so the
        award amount is snapshotted rather than recalculated live.
        """
        if self.coverage_type == 'full':
            return account.fee_structure.total_amount

        if self.coverage_type == 'partial_percentage':
            return (
                account.fee_structure.total_amount *
                self.coverage_percentage / Decimal('100')
            ).quantize(Decimal('0.01'))

        if self.coverage_type == 'partial_fixed':
            return self.coverage_amount

        if self.coverage_type == 'category_specific':
            category_amount = Decimal(
                str(account.fee_structure.breakdown.get(self.covered_category, 0))
            )
            return min(self.coverage_amount, category_amount)

        return Decimal('0.00')


class ScholarshipAward(BaseModelMixin):
    """
    One student's award under a Scholarship, applied against a specific
    fee account. amount_covered is snapshotted at award time via
    Scholarship.compute_award_amount() so it doesn't silently drift if
    the fee structure changes after the award is made.
    """

    STATUS_CHOICES = [
        ('pending',   'Pending Approval'),
        ('approved',  'Approved'),
        ('disbursed', 'Disbursed'),  # actively reducing the student's balance
        ('revoked',   'Revoked'),
    ]

    scholarship = models.ForeignKey(
        'Scholarship',
        on_delete=models.PROTECT,
        related_name='awards'
    )

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name='scholarship_awards'
    )

    account = models.ForeignKey(
        'StudentFeeAccount',
        on_delete=models.PROTECT,
        related_name='scholarship_awards',
        help_text="The fee account this award applies against.",
    )

    amount_covered = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scholarship_awards_approved',
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ('scholarship', 'account')
        ordering = ['-created_at']
        verbose_name = "Scholarship Award"
        verbose_name_plural = "Scholarship Awards"

    def __str__(self):
        return (f"{self.student} — {self.scholarship} — "
                f"KES {self.amount_covered} [{self.get_status_display()}]")

    def clean(self):
        super().clean()

        if self.account_id and self.student_id and self.account.student_id != self.student_id:
            raise ValidationError({
                'account': "This fee account does not belong to the awarded student."
            })
        if self.status == 'revoked' and not self.revoked_reason:
            raise ValidationError({
                'revoked_reason': "A reason is required when revoking an award."
            })

    def approve(self, by_user):
        if self.status != 'pending':
            return
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def disburse(self):
        if self.status != 'approved':
            return
        self.status = 'disbursed'
        self.save()

    def revoke(self, reason):
        self.status = 'revoked'
        self.revoked_reason = reason
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
# Installment plans
# ─────────────────────────────────────────────────────────────────────────────

class InstallmentPlan(BaseModelMixin):
    """
    A structured payment schedule against a single fee account, in place
    of paying the full balance in one lump sum. Installment.status is
    derived by sync_status() rather than tracked independently against
    Payment records, since Payment isn't installment-aware — call
    sync_status() after recording a payment (or run it periodically) to
    keep statuses current.
    """

    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('cancelled', 'Cancelled'),
    ]

    account = models.OneToOneField(
        'StudentFeeAccount',
        on_delete=models.CASCADE,
        related_name='installment_plan',
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installment_plans_approved',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Installment Plan"
        verbose_name_plural = "Installment Plans"

    def __str__(self):
        return f"Installment plan — {self.account} [{self.get_status_display()}]"

    @property
    def total_scheduled(self):
        total = self.installments.aggregate(
            total=models.Sum('amount_due'))['total']
        return total or Decimal('0.00')

    @property
    def is_fully_scheduled(self):
        """
        Whether the installments add up to the account's current
        amount_billed. Can drift if a Charge is added to the account after
        the plan was scheduled — check this before assuming the plan
        covers the full bill.
        """
        return self.total_scheduled == self.account.amount_billed

    def sync_status(self):
        """
        FIFO-settles the account's net_paid + scholarship coverage against
        installments in sequence order: marks each 'paid' once fully
        covered, 'overdue' if its due_date has passed and it isn't paid,
        else 'pending'. Marks the plan 'completed' once every non-waived
        installment is paid.
        """
        covered = self.account.net_paid + self.account.amount_scholarship
        today = timezone.now().date()
        all_paid = True

        for installment in self.installments.order_by('sequence'):
            if installment.status == 'waived':
                continue

            if covered >= installment.amount_due:
                installment.status = 'paid'
                covered -= installment.amount_due
            else:
                all_paid = False
                installment.status = 'overdue' if installment.due_date < today else 'pending'

            installment.save(update_fields=['status'])

        if all_paid and self.status == 'active':
            self.status = 'completed'
            self.save(update_fields=['status'])


class Installment(BaseModelMixin):
    """A single scheduled payment within an InstallmentPlan."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid',    'Paid'),
        ('overdue', 'Overdue'),
        ('waived',  'Waived'),
    ]

    plan = models.ForeignKey(
        'InstallmentPlan',
        on_delete=models.CASCADE,
        related_name='installments'
    )

    sequence = models.PositiveIntegerField(
        help_text="Order within the plan — 1, 2, 3…"
    )
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    class Meta:
        unique_together = ('plan', 'sequence')
        ordering = ['plan', 'sequence']
        verbose_name = "Installment"
        verbose_name_plural = "Installments"

    def __str__(self):
        return (f"{self.plan.account} — installment {self.sequence} — "
                f"KES {self.amount_due} due {self.due_date}")


# ─────────────────────────────────────────────────────────────────────────────
# Late fees
# ─────────────────────────────────────────────────────────────────────────────

class LateFeePolicy(BaseModelMixin):
    """
    Optional penalty policy attached to a FeeStructure. Applied via
    Charge.apply_late_fees(session), which is intended to run periodically
    (a daily management command / cron), not on every request.
    """

    PENALTY_TYPE_CHOICES = [
        ('fixed',      'Fixed Amount'),
        ('percentage', 'Percentage of Outstanding Balance'),
    ]

    fee_structure = models.OneToOneField(
        'FeeStructure',
        on_delete=models.CASCADE,
        related_name='late_fee_policy'
    )

    grace_period_days = models.PositiveIntegerField(
        default=14,
        help_text="Days past the account's due date (days_remaining) "
        "before a penalty applies.",
    )

    penalty_type = models.CharField(
        max_length=12,
        choices=PENALTY_TYPE_CHOICES,
        default='fixed'
    )
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    penalty_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Late Fee Policy"
        verbose_name_plural = "Late Fee Policies"

    def __str__(self):
        return f"Late fee policy — {self.fee_structure}"

    def clean(self):
        super().clean()

        if self.penalty_type == 'fixed' and self.penalty_amount is None:
            raise ValidationError({
                'penalty_amount': "Required when penalty_type='fixed'."
            })
        if self.penalty_type == 'percentage' and self.penalty_percentage is None:
            raise ValidationError({
                'penalty_percentage': "Required when penalty_type='percentage'."
            })
