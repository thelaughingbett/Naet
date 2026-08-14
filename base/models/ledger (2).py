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

"""
General ledger / chart of accounts.

This module is a *parallel, authoritative* accounting ledger — it does not
replace StudentFeeAccount/Payment/Refund/Charge in fees.py. Those stay the
operational subsidiary ledger (what the student portal, webhooks, and
finance-office staff actually interact with day to day). This module is fed
*from* those transactions via JournalEntry.for_payment()/for_refund(), so
Finance can produce a real trial balance / income statement / balance sheet
from posted journal entries, reconciled back against the subsidiary ledger
rather than duplicating its logic.

Open design question left for later: whether fee billing itself (creating a
StudentFeeAccount) should recognise revenue immediately (Dr Receivable /
Cr Tuition Revenue at billing time) or defer it across the session. That's
a real accounting-policy decision, not a technical one — deliberately not
assumed here.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from .base import BaseModelMixin


class Account(BaseModelMixin):
    """A single ledger account in the chart of accounts."""

    ACCOUNT_TYPE_CHOICES = [
        ('asset',     'Asset'),
        ('liability', 'Liability'),
        ('equity',    'Equity'),
        ('revenue',   'Revenue'),
        ('expense',   'Expense'),
    ]

    NORMAL_BALANCE_CHOICES = [
        ('debit',  'Debit'),
        ('credit', 'Credit'),
    ]

    # Kept in sync with Payment.PAYMENT_METHOD_CHOICES in fees.py by
    # convention, not by import — a plain string field rather than an FK
    # so this module doesn't need to depend on fees.py at all.
    PAYMENT_METHOD_CHOICES = [
        ('', '— Not a cash/bank account —'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]

    code = models.CharField(
        max_length=20, unique=True,
        help_text="e.g. '1010', '4100' — institution's own numbering scheme.",
    )
    name = models.CharField(max_length=150)

    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    normal_balance = models.CharField(max_length=6, choices=NORMAL_BALANCE_CHOICES)

    parent = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True,
        related_name='children',
    )

    is_active = models.BooleanField(default=True)

    is_control_account = models.BooleanField(
        default=False,
        help_text="A summary account (e.g. 'Accounts Receivable — Student "
                   "Fees') whose balance is expected to reconcile against a "
                   "subsidiary ledger (e.g. the sum of StudentFeeAccount "
                   "balances) rather than being meaningful on its own.",
    )

    is_default_receivable_account = models.BooleanField(
        default=False,
        help_text="The single account JournalEntry.for_payment()/for_refund() "
                   "post the receivable side of student-fee transactions "
                   "against. Only one active account may have this set.",
    )

    is_default_payable_account = models.BooleanField(
        default=False,
        help_text="The single Accounts Payable — Trade Creditors account "
                   "JournalEntry.for_vendor_invoice()/for_vendor_payment() "
                   "post against. Only one active account may have this set.",
    )

    is_default_salary_expense_account = models.BooleanField(
        default=False,
        help_text="The single Salaries & Wages Expense account "
                   "JournalEntry.for_payroll_run() debits gross pay plus "
                   "employer statutory contributions against. Only one "
                   "active account may have this set.",
    )

    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True, default='',
        help_text="Set on cash/bank-type accounts so JournalEntry.for_payment() "
                   "and for_vendor_payment()/for_payroll_run() can look up "
                   "which account a given method clears into. Leave blank "
                   "for non-cash accounts.",
    )

    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['code']
        verbose_name = "Ledger Account"
        verbose_name_plural = "Chart of Accounts"
        constraints = [
            models.UniqueConstraint(
                fields=['payment_method'],
                condition=models.Q(is_active=True) & ~models.Q(payment_method=''),
                name='unique_active_account_per_payment_method',
            ),
            models.UniqueConstraint(
                fields=['is_default_receivable_account'],
                condition=models.Q(is_active=True, is_default_receivable_account=True),
                name='unique_active_default_receivable_account',
            ),
            models.UniqueConstraint(
                fields=['is_default_payable_account'],
                condition=models.Q(is_active=True, is_default_payable_account=True),
                name='unique_active_default_payable_account',
            ),
            models.UniqueConstraint(
                fields=['is_default_salary_expense_account'],
                condition=models.Q(is_active=True, is_default_salary_expense_account=True),
                name='unique_active_default_salary_expense_account',
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def clean(self):
        super().clean()

        expected_normal_balance = {
            'asset': 'debit',
            'expense': 'debit',
            'liability': 'credit',
            'equity': 'credit',
            'revenue': 'credit',
        }
        if self.account_type and self.normal_balance != expected_normal_balance[self.account_type]:
            raise ValidationError({
                'normal_balance': f"{self.get_account_type_display()} accounts "
                                  f"normally carry a {expected_normal_balance[self.account_type]} balance."
            })

        if self.parent_id and self.parent.account_type != self.account_type:
            raise ValidationError({
                'parent': "A sub-account must share its parent's account_type."
            })

        if self.payment_method and self.account_type != 'asset':
            raise ValidationError({
                'payment_method': "Only an Asset account (cash/bank) can be "
                                  "tagged with a payment method."
            })

        if self.is_default_receivable_account and self.account_type != 'asset':
            raise ValidationError({
                'is_default_receivable_account': "Accounts Receivable is an Asset "
                                                  "— this flag belongs on an "
                                                  "asset-type account."
            })

        if self.is_default_payable_account and self.account_type != 'liability':
            raise ValidationError({
                'is_default_payable_account': "Accounts Payable is a Liability "
                                               "— this flag belongs on a "
                                               "liability-type account."
            })

        if self.is_default_salary_expense_account and self.account_type != 'expense':
            raise ValidationError({
                'is_default_salary_expense_account': "Salaries & Wages is an "
                                                       "Expense — this flag "
                                                       "belongs on an "
                                                       "expense-type account."
            })

    def balance_as_of(self, as_of=None):
        """
        This account's signed balance from posted journal entry lines only,
        expressed in the direction of its own normal_balance — i.e. a
        debit-normal account (Asset/Expense) with more debits than credits
        posted against it returns a positive number.
        """
        as_of = as_of or timezone.now().date()
        lines = self.journal_lines.filter(
            entry__status='posted', entry__entry_date__lte=as_of
        )
        debits = lines.filter(direction='debit').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        credits = lines.filter(direction='credit').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')

        if self.normal_balance == 'debit':
            return debits - credits
        return credits - debits

    @property
    def balance(self):
        return self.balance_as_of()

    @classmethod
    def trial_balance(cls, as_of=None):
        """
        Returns every active account with a non-zero balance as of `as_of`
        (defaults to today), laid out in natural debit/credit columns —
        the two column totals should be equal if the ledger is actually
        balanced. Shape:
            {
                'rows': [{'account': Account, 'debit': Decimal, 'credit': Decimal}, ...],
                'total_debit': Decimal,
                'total_credit': Decimal,
                'is_balanced': bool,
            }
        """
        as_of = as_of or timezone.now().date()
        rows = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        for account in cls.objects.filter(is_active=True).order_by('code'):
            balance = account.balance_as_of(as_of)
            if balance == 0:
                continue

            if account.normal_balance == 'debit':
                debit = balance if balance > 0 else Decimal('0.00')
                credit = -balance if balance < 0 else Decimal('0.00')
            else:
                credit = balance if balance > 0 else Decimal('0.00')
                debit = -balance if balance < 0 else Decimal('0.00')

            rows.append({'account': account, 'debit': debit, 'credit': credit})
            total_debit += debit
            total_credit += credit

        return {
            'rows': rows,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'is_balanced': total_debit == total_credit,
        }


class FiscalYear(BaseModelMixin):
    """
    A financial reporting year — deliberately separate from Session.
    Academic sessions (semesters) and an institution's fiscal/audit year
    (often July–June for Kenyan public entities) don't necessarily line
    up, so journal entries are posted against this, not Session.
    """

    name = models.CharField(max_length=20, unique=True, help_text="e.g. '2026/2027'.")
    start_date = models.DateField()
    end_date = models.DateField()

    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fiscal_years_closed',
    )

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Fiscal Year"
        verbose_name_plural = "Fiscal Years"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError({
                'end_date': "End date must be after the start date."
            })

        if self.start_date and self.end_date:
            overlapping = FiscalYear.objects.filter(
                start_date__lte=self.end_date, end_date__gte=self.start_date
            ).exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    "This fiscal year's dates overlap with an existing fiscal year."
                )

    @classmethod
    def current(cls):
        today = timezone.now().date()
        return cls.objects.filter(
            start_date__lte=today, end_date__gte=today, is_closed=False
        ).first()

    def close(self, by_user):
        if self.is_closed:
            return
        if self.journal_entries.filter(status='draft').exists():
            raise ValidationError(
                "Cannot close a fiscal year with draft journal entries still open."
            )
        self.is_closed = True
        self.closed_at = timezone.now()
        self.closed_by = by_user
        self.save()


class JournalEntry(BaseModelMixin):
    """
    A balanced batch of debit/credit lines posted to the ledger — the
    atomic unit of double-entry bookkeeping. Created either manually by
    finance staff, or automatically via source_type/source_id linking back
    to a Payment, Refund, Charge, ScholarshipAward, etc. (see for_payment()
    and for_refund() below for the automatic path).
    """

    SOURCE_TYPE_CHOICES = [
        ('manual',             'Manual Entry'),
        ('payment',            'Student Payment'),
        ('refund',             'Student Refund'),
        ('charge',             'Ad-hoc Charge'),
        ('scholarship_award',  'Scholarship Award'),
        ('fee_billing',        'Fee Structure Billing'),
        ('payroll',            'Payroll'),
        ('vendor_invoice',     'Vendor Invoice'),
        ('vendor_payment',     'Vendor Payment'),
        ('adjustment',         'Adjustment / Correction'),
    ]

    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('posted',   'Posted'),
        ('reversed', 'Reversed'),
    ]

    fiscal_year = models.ForeignKey(
        'FiscalYear', on_delete=models.PROTECT, related_name='journal_entries'
    )
    entry_date = models.DateField(default=timezone.now)

    reference = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Human-readable voucher/reference number.",
    )
    description = models.CharField(max_length=255)

    source_type = models.CharField(
        max_length=20, choices=SOURCE_TYPE_CHOICES, default='manual'
    )
    source_id = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="The originating record's record_id, loosely typed and "
                   "resolved against source_type rather than a hard FK — "
                   "keeps the ledger decoupled from every other app's models.",
    )

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='draft', db_index=True
    )

    prepared_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='journal_entries_prepared',
    )
    posted_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='journal_entries_posted',
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    reversal_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reversed_by',
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ['-entry_date', '-created_at']
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        return f"JE {self.reference or self.record_id} — {self.entry_date} [{self.get_status_display()}]"

    @property
    def total_debits(self):
        return self.lines.filter(direction='debit').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def total_credits(self):
        return self.lines.filter(direction='credit').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def is_balanced(self):
        return self.total_debits == self.total_credits

    def clean(self):
        super().clean()

        if self.fiscal_year_id and self.fiscal_year.is_closed and self._state.adding:
            raise ValidationError({
                'fiscal_year': "Cannot add entries to a closed fiscal year."
            })

        if self.entry_date and self.fiscal_year_id:
            if not (self.fiscal_year.start_date <= self.entry_date <= self.fiscal_year.end_date):
                raise ValidationError({
                    'entry_date': "Entry date must fall within the selected fiscal year."
                })

    def post(self, by_user):
        if self.status != 'draft':
            return
        if self.lines.count() < 2:
            raise ValidationError(
                "A journal entry needs at least two lines (one debit, one credit)."
            )
        if not self.is_balanced:
            raise ValidationError(
                f"Entry is not balanced: debits {self.total_debits} != "
                f"credits {self.total_credits}."
            )
        if self.fiscal_year.is_closed:
            raise ValidationError("Cannot post to a closed fiscal year.")

        self.status = 'posted'
        self.posted_by = by_user
        self.posted_at = timezone.now()
        self.save()

    def reverse(self, by_user, reason=""):
        """
        Creates and posts a mirror-image entry that cancels this one out.
        Posted history is never edited or deleted — a correction is always
        a new, linked entry.
        """
        if self.status != 'posted':
            raise ValidationError("Only a posted entry can be reversed.")

        reversal = JournalEntry.objects.create(
            fiscal_year=self.fiscal_year,
            entry_date=timezone.now().date(),
            reference=f"REV-{self.reference or self.record_id}",
            description=(f"Reversal of {self.reference or self.record_id}"
                         + (f": {reason}" if reason else "")),
            source_type='adjustment',
            prepared_by=by_user,
            reversal_of=self,
        )
        for line in self.lines.all():
            JournalEntryLine.objects.create(
                entry=reversal,
                account=line.account,
                direction='credit' if line.direction == 'debit' else 'debit',
                amount=line.amount,
                narration=f"Reversal of: {line.narration}" if line.narration else "Reversal",
            )
        reversal.post(by_user)

        self.status = 'reversed'
        self.save()
        return reversal

    # ── automatic posting from the student-fee subsidiary ledger ──────────

    @classmethod
    def for_payment(cls, payment, fiscal_year=None, by_user=None):
        """
        Creates and posts the standard entry for a completed Payment:
            Debit   Cash/Bank/M-Pesa clearing account    amount
            Credit  Accounts Receivable — Student Fees    amount

        Idempotent per payment (matched on source_type='payment' +
        source_id) — safe to call more than once, e.g. from
        Payment.confirm(), without risking a duplicate posting.
        """
        existing = cls.objects.filter(
            source_type='payment', source_id=str(payment.record_id)
        ).first()
        if existing:
            return existing

        fiscal_year = fiscal_year or FiscalYear.current()
        if not fiscal_year:
            raise ValidationError(
                "No open fiscal year found to post this payment into."
            )

        cash_account = Account.objects.filter(
            payment_method=payment.method, is_active=True
        ).first()
        if not cash_account:
            raise ValidationError(
                f"No ledger account configured for payment method '{payment.method}'."
            )

        receivable_account = Account.objects.filter(
            is_default_receivable_account=True, is_active=True
        ).first()
        if not receivable_account:
            raise ValidationError(
                "No default Accounts Receivable account configured."
            )

        entry = cls.objects.create(
            fiscal_year=fiscal_year,
            entry_date=payment.paid_at.date(),
            reference=payment.transaction_ref or str(payment.record_id),
            description=f"Payment received — {payment.account.student.registration_number}",
            source_type='payment',
            source_id=str(payment.record_id),
            prepared_by=by_user,
        )
        JournalEntryLine.objects.create(
            entry=entry, account=cash_account, direction='debit',
            amount=payment.amount, narration=payment.get_method_display(),
        )
        JournalEntryLine.objects.create(
            entry=entry, account=receivable_account, direction='credit',
            amount=payment.amount, narration=str(payment.account.student),
        )
        entry.post(by_user)
        return entry

    @classmethod
    def for_refund(cls, refund, fiscal_year=None, by_user=None):
        """
        Mirror image of for_payment():
            Debit   Accounts Receivable — Student Fees    amount
            Credit  Cash/Bank/M-Pesa clearing account      amount
        Same idempotency guarantee, keyed on source_type='refund'.
        """
        existing = cls.objects.filter(
            source_type='refund', source_id=str(refund.record_id)
        ).first()
        if existing:
            return existing

        fiscal_year = fiscal_year or FiscalYear.current()
        if not fiscal_year:
            raise ValidationError(
                "No open fiscal year found to post this refund into."
            )

        cash_account = Account.objects.filter(
            payment_method=refund.method, is_active=True
        ).first()
        receivable_account = Account.objects.filter(
            is_default_receivable_account=True, is_active=True
        ).first()
        if not cash_account or not receivable_account:
            raise ValidationError(
                "Ledger accounts are not fully configured for refunds."
            )

        entry = cls.objects.create(
            fiscal_year=fiscal_year,
            entry_date=(refund.processed_at or timezone.now()).date(),
            reference=refund.transaction_ref or str(refund.record_id),
            description=f"Refund issued — {refund.account.student.registration_number}",
            source_type='refund',
            source_id=str(refund.record_id),
            prepared_by=by_user,
        )
        JournalEntryLine.objects.create(
            entry=entry, account=receivable_account, direction='debit',
            amount=refund.amount, narration=str(refund.account.student),
        )
        JournalEntryLine.objects.create(
            entry=entry, account=cash_account, direction='credit',
            amount=refund.amount, narration=refund.get_method_display(),
        )
        entry.post(by_user)
        return entry

        # Charge and ScholarshipAward follow the identical for_x() pattern —
        # left unimplemented here since both need a policy decision first:
        # which Revenue/Expense account does each Charge.category or
        # Scholarship map to? That's a chart-of-accounts design question,
        # not a modeling one, so it's a natural next step once the chart
        # of accounts is actually populated.

    # ── automatic posting from the accounts-payable/procurement ledger ────

    @classmethod
    def for_vendor_invoice(cls, invoice, fiscal_year=None, by_user=None):
        """
        Recognises a vendor invoice as a liability:
            Debit   [each invoice line's account]      line.amount
            Credit  Accounts Payable — Trade Creditors  total_amount
        One entry per invoice, with one debit line per invoice line (a
        single invoice can hit several expense/asset accounts at once).
        Idempotent per invoice.
        """
        existing = cls.objects.filter(
            source_type='vendor_invoice', source_id=str(invoice.record_id)
        ).first()
        if existing:
            return existing

        fiscal_year = fiscal_year or FiscalYear.current()
        if not fiscal_year:
            raise ValidationError(
                "No open fiscal year found to post this invoice into."
            )

        payable_account = Account.objects.filter(
            is_default_payable_account=True, is_active=True
        ).first()
        if not payable_account:
            raise ValidationError("No default Accounts Payable account configured.")

        lines = list(invoice.lines.select_related('account'))
        if not lines:
            raise ValidationError("Cannot post an invoice with no lines.")
        for line in lines:
            if not line.account_id:
                raise ValidationError(
                    f"Invoice line '{line.description}' has no ledger account set."
                )

        entry = cls.objects.create(
            fiscal_year=fiscal_year,
            entry_date=invoice.invoice_date,
            reference=invoice.invoice_number,
            description=f"Vendor invoice — {invoice.vendor.name}",
            source_type='vendor_invoice',
            source_id=str(invoice.record_id),
            prepared_by=by_user,
        )
        for line in lines:
            JournalEntryLine.objects.create(
                entry=entry, account=line.account, direction='debit',
                amount=line.amount, narration=line.description,
            )
        JournalEntryLine.objects.create(
            entry=entry, account=payable_account, direction='credit',
            amount=invoice.total_amount, narration=invoice.vendor.name,
        )
        entry.post(by_user)
        return entry

    @classmethod
    def for_vendor_payment(cls, payment, fiscal_year=None, by_user=None):
        """
        Mirror image of for_vendor_invoice():
            Debit   Accounts Payable — Trade Creditors  amount
            Credit  Cash/Bank/Cheque clearing account     amount
        Uses the same payment_method → Account mapping as for_payment().
        """
        existing = cls.objects.filter(
            source_type='vendor_payment', source_id=str(payment.record_id)
        ).first()
        if existing:
            return existing

        fiscal_year = fiscal_year or FiscalYear.current()
        if not fiscal_year:
            raise ValidationError(
                "No open fiscal year found to post this payment into."
            )

        cash_account = Account.objects.filter(
            payment_method=payment.method, is_active=True
        ).first()
        payable_account = Account.objects.filter(
            is_default_payable_account=True, is_active=True
        ).first()
        if not cash_account or not payable_account:
            raise ValidationError(
                "Ledger accounts are not fully configured for vendor payments."
            )

        entry = cls.objects.create(
            fiscal_year=fiscal_year,
            entry_date=(payment.paid_at or timezone.now()).date(),
            reference=payment.reference or str(payment.record_id),
            description=f"Vendor payment — {payment.vendor.name}",
            source_type='vendor_payment',
            source_id=str(payment.record_id),
            prepared_by=by_user,
        )
        JournalEntryLine.objects.create(
            entry=entry, account=payable_account, direction='debit',
            amount=payment.amount, narration=payment.vendor.name,
        )
        JournalEntryLine.objects.create(
            entry=entry, account=cash_account, direction='credit',
            amount=payment.amount, narration=payment.get_method_display(),
        )
        entry.post(by_user)
        return entry

    # ── automatic posting from a finalized payroll run ─────────────────────

    @classmethod
    def for_payroll_run(cls, payroll_run, fiscal_year=None, by_user=None):
        """
        Posts one balanced entry for an entire finalized payroll run:
            Debit   Salaries & Wages Expense (default salary expense account)
                        = sum of gross_pay + employer-side statutory contributions
            Credit  Net pay clearing account (the active 'bank' payment_method account)
                        = sum of net_pay
            Credit  [each StatutoryDeductionType.remittance_payable_account]
                        = employee + employer amounts withheld for that type
            Credit  [each StaffDeductionMandate.gl_account in use this run]
                        = voluntary deduction amounts withheld
        Requires payroll.py's StatutoryDeductionType.remittance_payable_account
        and StaffDeductionMandate.gl_account to be configured — raises a
        clear error naming what's missing rather than silently skipping a
        line, since a payroll entry that's silently short a credit line
        would post unbalanced.
        Idempotent per run.
        """
        existing = cls.objects.filter(
            source_type='payroll', source_id=str(payroll_run.record_id)
        ).first()
        if existing:
            return existing

        if payroll_run.status not in ('finalized', 'paid'):
            raise ValidationError(
                "Can only post a finalized payroll run to the ledger."
            )

        fiscal_year = fiscal_year or FiscalYear.current()
        if not fiscal_year:
            raise ValidationError(
                "No open fiscal year found to post this payroll run into."
            )

        salary_expense_account = Account.objects.filter(
            is_default_salary_expense_account=True, is_active=True
        ).first()
        if not salary_expense_account:
            raise ValidationError("No default salary expense account configured.")

        clearing_account = Account.objects.filter(
            payment_method='bank', is_active=True
        ).first()
        if not clearing_account:
            raise ValidationError(
                "No active bank clearing account configured for net pay disbursement."
            )

        # Imported here rather than at module level to avoid a hard
        # ledger.py ↔ payroll.py import-order dependency; both modules
        # already reference each other only by string FK, this keeps that
        # symmetry for the one place an actual class reference is needed.
        from .payroll import PayslipLine

        total_expense = payroll_run.total_employer_cost
        total_net = payroll_run.total_net

        entry = cls.objects.create(
            fiscal_year=fiscal_year,
            entry_date=payroll_run.period.pay_date,
            reference=f"PAYROLL-{payroll_run.period.year}-{payroll_run.period.month:02d}-R{payroll_run.run_number}",
            description=f"Payroll — {payroll_run.period}",
            source_type='payroll',
            source_id=str(payroll_run.record_id),
            prepared_by=by_user,
        )

        JournalEntryLine.objects.create(
            entry=entry, account=salary_expense_account, direction='debit',
            amount=total_expense,
            narration="Gross salaries + employer statutory contributions",
        )
        JournalEntryLine.objects.create(
            entry=entry, account=clearing_account, direction='credit',
            amount=total_net, narration="Net pay disbursed",
        )

        statutory_lines = PayslipLine.objects.filter(
            payslip__run=payroll_run, statutory_deduction_type__isnull=False,
        ).exclude(category='voluntary').select_related('statutory_deduction_type')

        statutory_totals = {}
        for line in statutory_lines:
            key = line.statutory_deduction_type
            statutory_totals[key] = statutory_totals.get(key, Decimal('0.00')) + line.amount

        for deduction_type, amount in statutory_totals.items():
            if not deduction_type.remittance_payable_account_id:
                raise ValidationError(
                    f"No remittance payable account configured for {deduction_type.name}."
                )
            JournalEntryLine.objects.create(
                entry=entry, account=deduction_type.remittance_payable_account,
                direction='credit', amount=amount, narration=deduction_type.name,
            )

        voluntary_lines = PayslipLine.objects.filter(
            payslip__run=payroll_run, category='voluntary'
        ).select_related('deduction_mandate')

        voluntary_totals = {}
        for line in voluntary_lines:
            account = line.deduction_mandate.gl_account if line.deduction_mandate else None
            if not account:
                raise ValidationError(
                    f"No GL account configured for voluntary deduction '{line.description}'."
                )
            voluntary_totals[account] = voluntary_totals.get(account, Decimal('0.00')) + line.amount

        for account, amount in voluntary_totals.items():
            JournalEntryLine.objects.create(
                entry=entry, account=account, direction='credit',
                amount=amount, narration="Voluntary deduction",
            )

        entry.post(by_user)
        return entry


class JournalEntryLine(BaseModelMixin):
    """A single debit or credit line within a JournalEntry."""

    DIRECTION_CHOICES = [
        ('debit',  'Debit'),
        ('credit', 'Credit'),
    ]

    entry = models.ForeignKey(
        'JournalEntry', on_delete=models.CASCADE, related_name='lines'
    )
    account = models.ForeignKey(
        'Account', on_delete=models.PROTECT, related_name='journal_lines'
    )

    direction = models.CharField(max_length=6, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    narration = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ['entry', 'created_at']
        verbose_name = "Journal Entry Line"
        verbose_name_plural = "Journal Entry Lines"

    def __str__(self):
        return f"{self.entry} — {self.get_direction_display()} {self.amount} {self.account.code}"

    def clean(self):
        super().clean()

        if self.amount is not None and self.amount <= 0:
            raise ValidationError({
                'amount': "Amount must be positive — use 'direction' to "
                          "indicate debit vs credit, not a signed amount."
            })
