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
Bank reconciliation — matching what the bank statement says against what
Payment/Refund/VendorPayment records claim, and correcting the books for
whatever the bank shows that was never recorded internally (bank charges,
interest, dishonoured cheques).

Two kinds of "reconciling item" this module distinguishes:
  1. A bank statement line with no matching internal record — either
     matched manually/automatically to an existing Payment/Refund/
     VendorPayment (ReconciliationMatch), or, if nothing internal will
     ever explain it, corrected via a posted JournalEntry
     (ReconciliationAdjustment).
  2. A completed internal transaction with no matching bank statement
     line yet — a timing difference (the classic "outstanding cheque"),
     surfaced via BankReconciliation.outstanding_internal_transactions
     rather than requiring any action of its own.

KNOWN PRE-EXISTING SIMPLIFICATION this module inherits from ledger.py:
Account.payment_method assumes exactly one active ledger Account per
payment method institution-wide (enforced by a UniqueConstraint). That
means BankAccount below can represent one real bank account per method
cleanly, but an institution with, say, two separate bank-transfer
accounts (a fees collection account and a separate operations account)
can't currently express both as 'bank' simultaneously without a change to
that constraint. Not fixed here — flagged so it's not mistaken for new
scope creep introduced by this module.
"""

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from .base import BaseModelMixin


class BankAccount(BaseModelMixin):
    """
    A specific real-world bank/mobile-money account the institution holds
    — distinct from ledger.Account, which represents the GL balance.
    Reconciliation compares "what the GL says this account holds"
    (ledger_account.balance_as_of()) against "what the bank statement
    says" (BankStatementImport.closing_balance).
    """

    ACCOUNT_TYPE_CHOICES = [
        ('current',      'Current Account'),
        ('savings',      'Savings Account'),
        ('mobile_money', 'Mobile Money / Paybill'),
    ]

    ledger_account = models.OneToOneField(
        'Account',
        on_delete=models.PROTECT,
        related_name='bank_account',
        help_text="The GL account (Asset, cash/bank type) this real bank "
        "account's balance is tracked under.",
    )

    bank_name = models.CharField(max_length=150)
    account_name = models.CharField(
        max_length=150,
        help_text="Name on the account."
    )
    account_number = models.CharField(max_length=50)
    branch = models.CharField(max_length=100, blank=True, default="")
    currency = models.CharField(max_length=3, default='KES')

    account_type = models.CharField(
        max_length=15,
        choices=ACCOUNT_TYPE_CHOICES,
        default='current'
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('bank_name', 'account_number')
        ordering = ['bank_name', 'account_number']
        verbose_name = "Bank Account"
        verbose_name_plural = "Bank Accounts"

    def __str__(self):
        return f"{self.bank_name} — {self.account_number} ({self.account_name})"

    def clean(self):
        super().clean()
        if self.ledger_account_id and self.ledger_account.account_type != 'asset':
            raise ValidationError({
                'ledger_account': "A bank account's GL account must be an Asset."
            })

    @property
    def ledger_balance(self):
        """What the GL currently says this account holds."""
        return self.ledger_account.balance


class BankStatementImport(BaseModelMixin):
    """One batch import of a bank statement covering a date range."""

    STATUS_CHOICES = [
        ('pending',   'Pending Processing'),
        ('processed', 'Processed'),
        ('failed',    'Failed'),
    ]

    bank_account = models.ForeignKey(
        'BankAccount',
        on_delete=models.PROTECT,
        related_name='statement_imports'
    )

    statement_period_start = models.DateField()
    statement_period_end = models.DateField()

    file = models.FileField(
        upload_to='bank_statements/%Y/%m/',
        null=True, blank=True,
        help_text="Original statement file (CSV/PDF/MT940 etc.), if uploaded "
        "rather than entered manually.",
    )

    opening_balance = models.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    imported_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_statement_imports',
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    error_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-statement_period_end']
        verbose_name = "Bank Statement Import"
        verbose_name_plural = "Bank Statement Imports"

    def __str__(self):
        return f"{self.bank_account} — {self.statement_period_start} to {self.statement_period_end}"

    def clean(self):
        super().clean()
        if self.statement_period_end and self.statement_period_start and self.statement_period_end <= self.statement_period_start:
            raise ValidationError({
                'statement_period_end': "End date must be after the start date."
            })

    @property
    def total_debits(self):
        total = self.lines.filter(transaction_type='debit').aggregate(
            total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def total_credits(self):
        total = self.lines.filter(transaction_type='credit').aggregate(
            total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def is_balance_consistent(self):
        """
        Sanity-checks the statement's own internal math — opening balance
        plus credits (money in) minus debits (money out) should equal the
        closing balance. A mismatch here means the imported data itself
        is wrong/incomplete, before any reconciliation against the GL
        even starts.
        """
        return (self.opening_balance + self.total_credits - self.total_debits) == self.closing_balance


class BankStatementLine(BaseModelMixin):
    """One line item from an imported bank statement."""

    TRANSACTION_TYPE_CHOICES = [
        ('debit',  'Debit (Money Out)'),
        ('credit', 'Credit (Money In)'),
    ]
    MATCH_STATUS_CHOICES = [
        ('unmatched', 'Unmatched'),
        ('matched',   'Matched to Existing Transaction'),
        ('adjusted',  'Resolved via Adjustment Entry'),
        ('ignored',   'Ignored'),
    ]

    statement_import = models.ForeignKey(
        'BankStatementImport',
        on_delete=models.CASCADE,
        related_name='lines'
    )

    transaction_date = models.DateField()
    value_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date funds actually cleared, if different from transaction_date.",
    )

    description = models.CharField(max_length=255)
    bank_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="The bank's own transaction reference, if given.",
    )

    transaction_type = models.CharField(
        max_length=6,
        choices=TRANSACTION_TYPE_CHOICES
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    running_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    match_status = models.CharField(
        max_length=10,
        choices=MATCH_STATUS_CHOICES,
        default='unmatched',
        db_index=True
    )

    class Meta:
        ordering = ['statement_import', 'transaction_date']
        verbose_name = "Bank Statement Line"
        verbose_name_plural = "Bank Statement Lines"

    def __str__(self):
        sign = '-' if self.transaction_type == 'debit' else '+'
        return f"{self.transaction_date} — {sign}KES {self.amount} — {self.description}"

    @property
    def bank_account(self):
        return self.statement_import.bank_account

    def ignore(self):
        """For lines that need no reconciling action at all — e.g. an
        internal transfer between two of the institution's own accounts
        that's out of scope for this reconciliation."""
        self.match_status = 'ignored'
        self.save()


class ReconciliationMatch(BaseModelMixin):
    """
    Links a BankStatementLine to the internal transaction it corresponds
    to. Uses the same loosely-typed source_type/source_id string pattern
    as JournalEntry (ledger.py) rather than a GenericForeignKey, since a
    bank line could match a student Payment, a Refund, a VendorPayment,
    a payroll net-pay disbursement, or a manually-posted journal line.
    """

    SOURCE_TYPE_CHOICES = [
        ('payment',        'Student Payment'),
        ('refund',         'Student Refund'),
        ('vendor_payment', 'Vendor Payment'),
        ('payroll',        'Payroll Run (net pay disbursement)'),
        ('journal_line',   'Manual Journal Entry Line'),
        ('other',          'Other'),
    ]
    MATCH_TYPE_CHOICES = [
        ('auto',   'Automatic'),
        ('manual', 'Manual'),
    ]

    statement_line = models.OneToOneField(
        'BankStatementLine',
        on_delete=models.CASCADE,
        related_name='match'
    )

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    source_id = models.CharField(max_length=64)

    match_type = models.CharField(
        max_length=10,
        choices=MATCH_TYPE_CHOICES,
        default='manual'
    )
    matched_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="The internal transaction's amount, captured here so a "
        "variance is still detectable even if the source record "
        "changes later.",
    )

    matched_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_matches',
    )
    matched_at = models.DateTimeField(auto_now_add=True)

    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ['-matched_at']
        verbose_name = "Reconciliation Match"
        verbose_name_plural = "Reconciliation Matches"

    def __str__(self):
        return f"{self.statement_line} ↔ {self.source_type}:{self.source_id}"

    @property
    def variance(self):
        """Bank line amount minus the matched internal amount — should be
        zero for a clean match."""
        return self.statement_line.amount - self.matched_amount

    @property
    def has_variance(self):
        return self.variance != 0

    @classmethod
    def create_manual(cls, statement_line, source_type, source_obj, by_user, notes=""):
        return cls.objects.create(
            statement_line=statement_line, source_type=source_type,
            source_id=str(source_obj.record_id), match_type='manual',
            matched_amount=source_obj.amount, matched_by=by_user, notes=notes,
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.statement_line.match_status == 'unmatched':
            self.statement_line.match_status = 'matched'
            self.statement_line.save(update_fields=['match_status'])

    def delete(self, *args, **kwargs):
        """Undoing a match reverts the statement line to 'unmatched'
        rather than leaving it stuck showing 'matched' with nothing behind it."""
        line = self.statement_line
        super().delete(*args, **kwargs)
        line.match_status = 'unmatched'
        line.save(update_fields=['match_status'])


class ReconciliationAdjustment(BaseModelMixin):
    """
    A correcting entry for a BankStatementLine that has no corresponding
    internal transaction to match against — bank charges, interest
    earned, a dishonoured cheque reversal, etc. post() creates and posts
    the actual JournalEntry that brings the GL in line with what the bank
    statement shows. Once posted, this is never deleted — a mistaken
    adjustment gets corrected via JournalEntry.reverse() on its linked
    entry, the same as any other posted journal entry.
    """

    CATEGORY_CHOICES = [
        ('bank_charges',       'Bank Charges'),
        ('interest_earned',    'Interest Earned'),
        ('interest_charged',   'Interest / Overdraft Charges'),
        ('dishonoured_cheque', 'Dishonoured Cheque'),
        ('correction',         'Correction of Prior Error'),
        ('other',              'Other'),
    ]

    statement_line = models.OneToOneField(
        'BankStatementLine',
        on_delete=models.CASCADE,
        related_name='adjustment'
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    offsetting_account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='reconciliation_adjustments',
        help_text="The other side of the correcting entry — e.g. a Bank "
        "Charges Expense account, or an Interest Income account.",
    )

    journal_entry = models.OneToOneField(
        'JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_adjustment',
    )

    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_adjustments_created',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Reconciliation Adjustment"
        verbose_name_plural = "Reconciliation Adjustments"

    def __str__(self):
        return f"Adjustment — {self.statement_line} — {self.get_category_display()}"

    def post(self, by_user, fiscal_year=None):
        """
        Creates and posts the correcting entry:
          Credit statement line (money in, e.g. interest earned):
              Debit  this bank account's ledger account    amount
              Credit offsetting_account                     amount
          Debit statement line (money out, e.g. bank charges):
              Debit  offsetting_account                     amount
              Credit this bank account's ledger account    amount
        Idempotent — returns the existing entry if already posted.
        """
        from .ledger import JournalEntry, JournalEntryLine, FiscalYear

        if self.journal_entry_id:
            return self.journal_entry

        fiscal_year = fiscal_year or FiscalYear.current()
        if not fiscal_year:
            raise ValidationError(
                "No open fiscal year found to post this adjustment into."
            )

        line = self.statement_line
        bank_ledger_account = line.bank_account.ledger_account

        entry = JournalEntry.objects.create(
            fiscal_year=fiscal_year,
            entry_date=line.transaction_date,
            reference=line.bank_reference or f"RECON-ADJ-{self.record_id}",
            description=f"Reconciliation adjustment — {self.get_category_display()} — {line.description}",
            source_type='adjustment',
            source_id=str(self.record_id),
            prepared_by=by_user,
        )

        if line.transaction_type == 'credit':
            JournalEntryLine.objects.create(
                entry=entry, account=bank_ledger_account, direction='debit',
                amount=line.amount, narration=line.description,
            )
            JournalEntryLine.objects.create(
                entry=entry, account=self.offsetting_account, direction='credit',
                amount=line.amount, narration=self.get_category_display(),
            )
        else:
            JournalEntryLine.objects.create(
                entry=entry, account=self.offsetting_account, direction='debit',
                amount=line.amount, narration=self.get_category_display(),
            )
            JournalEntryLine.objects.create(
                entry=entry, account=bank_ledger_account, direction='credit',
                amount=line.amount, narration=line.description,
            )

        entry.post(by_user)

        self.journal_entry = entry
        self.save()

        line.match_status = 'adjusted'
        line.save(update_fields=['match_status'])

        return entry


class BankReconciliation(BaseModelMixin):
    """
    The periodic (typically monthly) reconciliation exercise for a single
    BankAccount. Reconciles the GL's live-computed balance against the
    imported statement's closing_balance, surfacing two kinds of
    reconciling item along the way — unmatched bank lines (see
    unmatched_bank_lines) and outstanding internal transactions not yet
    cleared by the bank (see outstanding_internal_transactions).
    """

    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('balanced',    'Balanced'),
        # signed off, possibly with an accepted residual variance
        ('completed',   'Completed'),
    ]

    bank_account = models.ForeignKey(
        'BankAccount',
        on_delete=models.PROTECT,
        related_name='reconciliations'
    )
    statement_import = models.ForeignKey(
        'BankStatementImport',
        on_delete=models.PROTECT,
        related_name='reconciliations'
    )

    period_start = models.DateField()
    period_end = models.DateField()

    ledger_opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )
    ledger_closing_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Filled in once reconciliation completes — the GL "
        "balance as of period_end.",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='in_progress',
        db_index=True
    )

    reconciled_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_reconciliations_completed',
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)

    variance_notes = models.TextField(
        blank=True,
        default="",
        help_text="Explanation for any residual variance accepted at sign-off.",
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('bank_account', 'period_end')
        ordering = ['-period_end']
        verbose_name = "Bank Reconciliation"
        verbose_name_plural = "Bank Reconciliations"

    def __str__(self):
        return f"{self.bank_account} — reconciliation to {self.period_end} [{self.get_status_display()}]"

    def clean(self):
        super().clean()
        if self.period_end and self.period_start and self.period_end <= self.period_start:
            raise ValidationError({
                'period_end': "End date must be after the start date."
            })

    @property
    def unmatched_bank_lines(self):
        return self.statement_import.lines.filter(match_status='unmatched')

    @property
    def outstanding_count(self):
        return self.unmatched_bank_lines.count()

    @property
    def calculated_ledger_closing_balance(self):
        """What the GL says this account holds as of period_end, computed live."""
        return self.bank_account.ledger_account.balance_as_of(self.period_end)

    @property
    def variance(self):
        """Bank statement's closing balance minus the GL's calculated
        closing balance — should be zero once every reconciling item is
        either matched or adjusted."""
        return self.statement_import.closing_balance - self.calculated_ledger_closing_balance

    @property
    def is_balanced(self):
        return self.variance == 0 and self.outstanding_count == 0

    @property
    def total_unmatched_amount(self):
        """Net effect (credits minus debits) of everything still unmatched
        on the bank statement side — a quick 'how far off are we' figure."""
        lines = self.unmatched_bank_lines
        credits = lines.filter(transaction_type='credit').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        debits = lines.filter(transaction_type='debit').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        return credits - debits

    def auto_match(self, date_tolerance_days=3, amount_tolerance=Decimal('0.01')):
        """
        Attempts automatic matching for every unmatched line in this
        reconciliation's statement import against completed Payment/
        Refund/VendorPayment records on the same payment method, within
        `amount_tolerance` and `date_tolerance_days` of the statement
        line's date. Only auto-matches when exactly one candidate is
        found for a line — zero or multiple candidates are left for
        manual review rather than guessed at. Payroll net-pay
        disbursements are deliberately excluded from auto-matching (a
        payroll run's bank line is often one bulk transfer covering many
        staff, which doesn't reduce to a single reliable amount/date
        match) — link those manually via ReconciliationMatch.create_manual().
        Returns the number of lines matched.
        """
        from .fees import Payment, Refund
        from .procurement import VendorPayment

        matched_count = 0
        method = self.bank_account.ledger_account.payment_method

        already_matched = {
            'payment': set(
                ReconciliationMatch.objects.filter(
                    source_type='payment'
                ).values_list('source_id', flat=True)
            ),
            'refund': set(
                ReconciliationMatch.objects.filter(
                    source_type='refund'
                ).values_list('source_id', flat=True)
            ),
            'vendor_payment': set(
                ReconciliationMatch.objects.filter(
                    source_type='vendor_payment'
                ).values_list(
                    'source_id', flat=True
                )
            ),
        }

        for line in self.unmatched_bank_lines:
            date_min = line.transaction_date - \
                datetime.timedelta(days=date_tolerance_days)
            date_max = line.transaction_date + \
                datetime.timedelta(days=date_tolerance_days)
            amount_min = line.amount - amount_tolerance
            amount_max = line.amount + amount_tolerance

            candidates = []
            if line.transaction_type == 'credit':
                qs = Payment.objects.filter(
                    method=method, status='completed',
                    paid_at__date__gte=date_min, paid_at__date__lte=date_max,
                    amount__gte=amount_min, amount__lte=amount_max,
                )
                candidates = [
                    ('payment', p) for p in qs
                    if str(p.record_id) not in already_matched['payment']
                ]
            else:
                refund_qs = Refund.objects.filter(
                    method=method, status='completed',
                    processed_at__date__gte=date_min, processed_at__date__lte=date_max,
                    amount__gte=amount_min, amount__lte=amount_max,
                )
                candidates += [
                    ('refund', r) for r in refund_qs
                    if str(r.record_id) not in already_matched['refund']
                ]

                vp_qs = VendorPayment.objects.filter(
                    method=method, status='completed',
                    paid_at__date__gte=date_min, paid_at__date__lte=date_max,
                    amount__gte=amount_min, amount__lte=amount_max,
                )
                candidates += [
                    ('vendor_payment', vp) for vp in vp_qs
                    if str(vp.record_id) not in already_matched['vendor_payment']
                ]

            if len(candidates) == 1:
                source_type, obj = candidates[0]
                ReconciliationMatch.objects.create(
                    statement_line=line, source_type=source_type,
                    source_id=str(obj.record_id), match_type='auto',
                    matched_amount=obj.amount,
                )
                already_matched[source_type].add(str(obj.record_id))
                matched_count += 1

        return matched_count

    @property
    def outstanding_internal_transactions(self):
        """
        Completed internal transactions on this bank account, dated
        within the reconciliation period, with no matching bank statement
        line yet — the classic timing-difference "outstanding cheque"
        case, shown here for visibility rather than requiring any action.
        Returns a plain list of (source_type, object) tuples since it
        spans three different models.
        """
        from .fees import Payment, Refund
        from .procurement import VendorPayment

        method = self.bank_account.ledger_account.payment_method
        already_matched = {
            'payment': set(ReconciliationMatch.objects.filter(
                source_type='payment').values_list('source_id', flat=True)),
            'refund': set(ReconciliationMatch.objects.filter(
                source_type='refund').values_list('source_id', flat=True)),
            'vendor_payment': set(ReconciliationMatch.objects.filter(
                source_type='vendor_payment').values_list('source_id', flat=True)),
        }

        outstanding = []

        for p in Payment.objects.filter(
            method=method, status='completed',
            paid_at__date__gte=self.period_start, paid_at__date__lte=self.period_end,
        ):
            if str(p.record_id) not in already_matched['payment']:
                outstanding.append(('payment', p))

        for r in Refund.objects.filter(
            method=method, status='completed',
            processed_at__date__gte=self.period_start, processed_at__date__lte=self.period_end,
        ):
            if str(r.record_id) not in already_matched['refund']:
                outstanding.append(('refund', r))

        for vp in VendorPayment.objects.filter(
            method=method, status='completed',
            paid_at__date__gte=self.period_start, paid_at__date__lte=self.period_end,
        ):
            if str(vp.record_id) not in already_matched['vendor_payment']:
                outstanding.append(('vendor_payment', vp))

        return outstanding

    def complete(self, by_user, accept_variance_reason=""):
        """
        Signs off the reconciliation. Requires a fully balanced state
        (zero variance, nothing unmatched) unless accept_variance_reason
        is given — mirrors real sign-off practice, where a small residual
        variance sometimes gets accepted and documented rather than
        chased indefinitely.
        """
        if not self.is_balanced and not accept_variance_reason:
            raise ValidationError(
                f"Cannot complete: variance of KES {self.variance} remains "
                f"and {self.outstanding_count} bank line(s) are still "
                f"unmatched. Provide accept_variance_reason to sign off anyway."
            )

        self.ledger_closing_balance = self.calculated_ledger_closing_balance
        self.status = 'balanced' if self.is_balanced else 'completed'
        self.reconciled_by = by_user
        self.reconciled_at = timezone.now()
        if accept_variance_reason:
            self.variance_notes = accept_variance_reason
        self.save()
