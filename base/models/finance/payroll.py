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
Payroll — staff salaries, statutory deductions, and remittance compliance.

DELIBERATE DESIGN CHOICE: Kenyan statutory rates (NSSF, SHIF, Affordable
Housing Levy, PAYE bands, personal relief) change frequently and are, as of
this writing, disputed even between recent official-adjacent sources on
exact current figures (NSSF's upper earnings limit in particular). Nothing
here hardcodes a rate, cap, or tax band as a Python constant — every rate
is effective-dated data (StatutoryRate, PayeTaxBand, PayeRelief) that must
be seeded/maintained from the current official KRA/NSSF/SHA notice at
deployment time, and re-seeded whenever those bodies change a figure. Do
not trust any rate baked into a seed script's initial values without
checking it against the current gazette notice first.

Workflow: PayrollPeriod (a calendar month) → PayrollRun (an execution,
re-runnable before finalization) → Payslip (one per staff member) →
PayslipLine (itemised earnings/deductions) → StatutoryRemittance (the
compliance obligation to actually pay NSSF/SHA/KRA/Housing Levy Fund by
the 9th of the following month).
"""

import calendar
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


# ─────────────────────────────────────────────────────────────────────────────
# Statutory rate configuration (data, not code — see module docstring)
# ─────────────────────────────────────────────────────────────────────────────

class StatutoryDeductionType(BaseModelMixin):
    """Reference row for a mandatory payroll deduction/contribution."""

    CODE_CHOICES = [
        ('nssf', 'NSSF — National Social Security Fund'),
        ('shif', 'SHIF — Social Health Insurance Fund'),
        ('ahl',  'Affordable Housing Levy'),
        ('nita', 'NITA Training Levy'),
        ('paye', 'PAYE — Pay As You Earn'),
    ]  # this could be strategy ??

    code = models.CharField(
        max_length=10,
        choices=CODE_CHOICES,
        unique=True
    )
    name = models.CharField(max_length=100)
    remitted_to = models.CharField(
        max_length=150,
        help_text="e.g. 'Social Health Authority (SHA)', 'NSSF', "
        "'Kenya Revenue Authority (KRA)'.",
    )

    is_employer_matched = models.BooleanField(
        default=False,
        help_text="Whether the employer pays a matching contribution on "
        "top of the employee deduction (e.g. NSSF, AHL) as "
        "opposed to withholding only (e.g. SHIF).",
    )
    is_allowable_before_paye = models.BooleanField(
        default=True,
        help_text="Whether this deduction is subtracted from gross pay "
        "before computing PAYE taxable pay.",
    )
    is_active = models.BooleanField(default=True)

    remittance_payable_account = models.ForeignKey(
        'Account',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='statutory_deduction_types',
        help_text="The liability account this deduction's withheld "
        "amounts credit to, for JournalEntry.for_payroll_run().",
    )

    class Meta:
        ordering = ['code']
        verbose_name = "Statutory Deduction Type"
        verbose_name_plural = "Statutory Deduction Types"

    def __str__(self):
        return self.name


class StatutoryRate(BaseModelMixin):
    """
    Effective-dated flat-percentage rate configuration for NSSF/SHIF/AHL/
    NITA (PAYE uses PayeTaxBand instead, since it's progressive, not flat).
    """

    deduction_type = models.ForeignKey(
        'StatutoryDeductionType',
        on_delete=models.PROTECT,
        related_name='rates'
    )

    employee_percentage = models.DecimalField(max_digits=5, decimal_places=3)
    employer_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Leave blank if the deduction type isn't employer-matched.",
    )

    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Floor amount regardless of the percentage calculation "
        "(e.g. SHIF's minimum monthly deduction).",
    )
    maximum_pensionable_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Upper earnings limit the percentage applies against — "
        "the deduction stops growing once gross pay exceeds "
        "this. Leave blank for uncapped deductions (e.g. SHIF, AHL).",
    )

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['deduction_type', '-effective_from']
        verbose_name = "Statutory Rate"
        verbose_name_plural = "Statutory Rates"

    def __str__(self):
        return f"{self.deduction_type.code.upper()} — {self.employee_percentage}% (from {self.effective_from})"

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_from and self.effective_to <= self.effective_from:
            raise ValidationError({
                'effective_to': "End date must be after the start date."
            })

    @classmethod
    def active_for(cls, code, as_of=None):
        as_of = as_of or timezone.now().date()
        return cls.objects.filter(
            deduction_type__code=code, effective_from__lte=as_of
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(
                effective_to__gte=as_of)
        ).order_by('-effective_from').first()

    def compute_employee_amount(self, gross_pay):
        base = min(
            gross_pay, self.maximum_pensionable_pay) if self.maximum_pensionable_pay else gross_pay
        amount = (base * self.employee_percentage /
                  Decimal('100')).quantize(Decimal('0.01'))
        if self.minimum_amount and amount < self.minimum_amount:
            amount = self.minimum_amount
        return amount

    def compute_employer_amount(self, gross_pay):
        if self.employer_percentage is None:
            return Decimal('0.00')
        base = min(
            gross_pay, self.maximum_pensionable_pay) if self.maximum_pensionable_pay else gross_pay
        return (base * self.employer_percentage / Decimal('100')).quantize(Decimal('0.01'))


class PayeTaxBand(BaseModelMixin):
    """
    One progressive PAYE tax band. A full band set for an effective period
    should be contiguous from 0 upward, with the top band's upper_bound
    left blank (unbounded).
    """

    lower_bound = models.DecimalField(max_digits=12, decimal_places=2)
    upper_bound = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank for the top, unbounded band.",
    )
    rate_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['effective_from', 'lower_bound']
        verbose_name = "PAYE Tax Band"
        verbose_name_plural = "PAYE Tax Bands"

    def __str__(self):
        top = f"KES {self.upper_bound}" if self.upper_bound is not None else "and above"
        return f"KES {self.lower_bound} to {top} — {self.rate_percentage}%"

    def clean(self):
        super().clean()
        if self.upper_bound is not None and self.upper_bound <= self.lower_bound:
            raise ValidationError({
                'upper_bound': "Upper bound must be greater than the lower bound."
            })

    @classmethod
    def active_bands(cls, as_of=None):
        as_of = as_of or timezone.now().date()
        return cls.objects.filter(effective_from__lte=as_of).filter(
            models.Q(effective_to__isnull=True) | models.Q(
                effective_to__gte=as_of)
        ).order_by('lower_bound')

    @classmethod
    def calculate_tax(cls, taxable_pay, as_of=None):
        """Progressive tax across contiguous bands, before personal relief."""
        tax = Decimal('0.00')
        for band in cls.active_bands(as_of):
            if taxable_pay <= band.lower_bound:
                break
            band_top = band.upper_bound if band.upper_bound is not None else taxable_pay
            taxed_amount = min(taxable_pay, band_top) - band.lower_bound
            if taxed_amount > 0:
                tax += taxed_amount * band.rate_percentage / Decimal('100')
        return tax.quantize(Decimal('0.01'))


class PayeRelief(BaseModelMixin):
    """
    Personal relief subtracted from computed PAYE tax (not from taxable
    pay) — effective-dated since KRA periodically revises it.
    """

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-effective_from']
        verbose_name = "PAYE Personal Relief"
        verbose_name_plural = "PAYE Personal Relief Rates"

    def __str__(self):
        return f"KES {self.amount}/month (from {self.effective_from})"

    @classmethod
    def amount_as_of(cls, as_of=None):
        as_of = as_of or timezone.now().date()
        relief = cls.objects.filter(effective_from__lte=as_of).filter(
            models.Q(effective_to__isnull=True) | models.Q(
                effective_to__gte=as_of)
        ).order_by('-effective_from').first()
        return relief.amount if relief else Decimal('0.00')


# ─────────────────────────────────────────────────────────────────────────────
# Staff compensation
# ─────────────────────────────────────────────────────────────────────────────

class StaffCompensation(BaseModelMixin):
    """
    Effective-dated basic salary for a staff member. A raise/promotion
    creates a new row rather than editing the old one, preserving exactly
    what was paid historically even if compensation changes later.
    """

    staff = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='compensation_history',
        limit_choices_to={'is_staff': True},
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['staff', '-effective_from']
        verbose_name = "Staff Compensation"
        verbose_name_plural = "Staff Compensation Records"

    def __str__(self):
        return f"{self.staff} — KES {self.basic_salary} (from {self.effective_from})"

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_from and self.effective_to <= self.effective_from:
            raise ValidationError({
                'effective_to': "End date must be after the start date."
            })

    @classmethod
    def active_for(cls, staff, as_of=None):
        as_of = as_of or timezone.now().date()
        return cls.objects.filter(staff=staff, effective_from__lte=as_of).filter(
            models.Q(effective_to__isnull=True) | models.Q(
                effective_to__gte=as_of)
        ).order_by('-effective_from').first()


class SalaryAllowance(BaseModelMixin):
    """A recurring allowance on top of basic salary."""

    CATEGORY_CHOICES = [
        ('house',          'House Allowance'),
        ('transport',      'Transport / Commuter Allowance'),
        ('medical',        'Medical Allowance'),
        ('responsibility', 'Responsibility / Acting Allowance'),
        ('leave',          'Leave Allowance'),
        ('other',          'Other'),
    ]

    staff = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='salary_allowances',
        limit_choices_to={'is_staff': True},
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    is_taxable = models.BooleanField(
        default=True,
        help_text="Whether this allowance counts toward taxable pay for PAYE.",
    )

    effective_from = models.DateField(default=timezone.now)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['staff', 'category']
        verbose_name = "Salary Allowance"
        verbose_name_plural = "Salary Allowances"

    def __str__(self):
        return f"{self.staff} — {self.get_category_display()} KES {self.amount}"

    @classmethod
    def active_for(cls, staff, as_of=None):
        as_of = as_of or timezone.now().date()
        return cls.objects.filter(staff=staff, effective_from__lte=as_of).filter(
            models.Q(effective_to__isnull=True) | models.Q(
                effective_to__gte=as_of)
        )


class StaffLoan(BaseModelMixin):
    """An institution-issued staff advance/loan, recovered via payroll
    through a linked StaffDeductionMandate."""

    STATUS_CHOICES = [
        ('active',      'Active'),
        ('completed',   'Completed'),
        ('written_off', 'Written Off'),
    ]

    staff = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='staff_loans',
        limit_choices_to={'is_staff': True},
    )
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    disbursed_date = models.DateField(default=timezone.now)
    monthly_installment = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        ordering = ['-disbursed_date']
        verbose_name = "Staff Loan"
        verbose_name_plural = "Staff Loans"

    def __str__(self):
        return f"Loan — {self.staff} — KES {self.principal_amount} [{self.get_status_display()}]"

    @property
    def amount_repaid(self):
        total = PayslipLine.objects.filter(
            deduction_mandate__loan=self,
            payslip__run__status__in=['finalized', 'paid'],
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def balance(self):
        return self.principal_amount - self.amount_repaid


class StaffDeductionMandate(BaseModelMixin):
    """
    A recurring voluntary deduction — SACCO contribution, union dues,
    staff loan repayment installment, voluntary insurance premium, etc.
    """

    CATEGORY_CHOICES = [
        ('sacco',          'SACCO Contribution'),
        ('union',          'Union Dues'),
        ('loan_repayment', 'Staff Loan Repayment'),
        ('insurance',      'Voluntary Insurance Premium'),
        ('other',          'Other'),
    ]

    staff = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='deduction_mandates',
        limit_choices_to={'is_staff': True},
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        default=""
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    loan = models.ForeignKey(
        'StaffLoan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deduction_mandates',
        help_text="Set when category='loan_repayment' — links this "
        "recurring deduction back to the loan it's paying down.",
    )

    gl_account = models.ForeignKey(
        'Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_deduction_mandates',
        help_text="Where this deduction's credit side posts — typically a "
        "'Staff Loans Receivable' asset account for loan "
        "repayments (reducing what's owed), or a third-party "
        "payable liability account for SACCO/union dues.",
    )

    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=timezone.now)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['staff', 'category']
        verbose_name = "Staff Deduction Mandate"
        verbose_name_plural = "Staff Deduction Mandates"

    def __str__(self):
        return f"{self.staff} — {self.get_category_display()} KES {self.amount}"

    def clean(self):
        super().clean()
        if self.category == 'loan_repayment' and not self.loan_id:
            raise ValidationError({
                'loan': "A loan repayment mandate must link to the StaffLoan it's repaying."
            })

    @classmethod
    def active_for(cls, staff, as_of=None):
        as_of = as_of or timezone.now().date()
        return cls.objects.filter(staff=staff, is_active=True, effective_from__lte=as_of).filter(
            models.Q(effective_to__isnull=True) | models.Q(
                effective_to__gte=as_of)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Payroll runs
# ─────────────────────────────────────────────────────────────────────────────

class PayrollPeriod(BaseModelMixin):
    """A calendar month payroll is run for."""

    STATUS_CHOICES = [
        ('open',       'Open'),
        ('processing', 'Processing'),
        ('finalized',  'Finalized'),
        ('paid',       'Paid'),
        ('closed',     'Closed'),
    ]

    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    pay_date = models.DateField()

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='open',
        db_index=True
    )

    class Meta:
        unique_together = ('month', 'year')
        ordering = ['-year', '-month']
        verbose_name = "Payroll Period"
        verbose_name_plural = "Payroll Periods"

    def __str__(self):
        return f"Payroll {self.month:02d}/{self.year} [{self.get_status_display()}]"

    def clean(self):
        super().clean()
        if not (1 <= self.month <= 12):
            raise ValidationError({'month': "Month must be between 1 and 12."})

    @property
    def period_end_date(self):
        last_day = calendar.monthrange(self.year, self.month)[1]
        return datetime.date(self.year, self.month, last_day)

    @property
    def remittance_due_date(self):
        """Statutory remittances are due by the 9th of the following month."""
        if self.month == 12:
            return datetime.date(self.year + 1, 1, 9)
        return datetime.date(self.year, self.month + 1, 9)


class PayrollRun(BaseModelMixin):
    """
    One execution of payroll for a PayrollPeriod. run_number increments
    if a period needs recomputing after a correction — old runs aren't
    edited or deleted, a new numbered run supersedes them.
    """

    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('computed',  'Computed'),
        ('approved',  'Approved'),
        ('finalized', 'Finalized'),
        ('paid',      'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    period = models.ForeignKey(
        'PayrollPeriod',
        on_delete=models.PROTECT,
        related_name='runs'
    )
    run_number = models.PositiveIntegerField(
        default=1,
        help_text="Increments if this period's payroll needs to be "
        "recomputed/rerun after corrections.",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    run_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_runs_executed',
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_runs_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('period', 'run_number')
        ordering = ['-period', '-run_number']
        verbose_name = "Payroll Run"
        verbose_name_plural = "Payroll Runs"

    def __str__(self):
        return f"{self.period} — run {self.run_number} [{self.get_status_display()}]"

    @property
    def total_gross(self):
        total = self.payslips.aggregate(total=models.Sum('gross_pay'))['total']
        return total or Decimal('0.00')

    @property
    def total_net(self):
        total = self.payslips.aggregate(total=models.Sum('net_pay'))['total']
        return total or Decimal('0.00')

    @property
    def total_employer_cost(self):
        total = self.payslips.aggregate(
            total=models.Sum('total_employer_cost'))['total']
        return total or Decimal('0.00')

    def compute(self, staff_queryset=None, as_of=None):
        """
        Generates/refreshes a Payslip for every active staff member with a
        StaffCompensation record as of the period's pay_date. Safe to call
        more than once on a draft/computed run — clears and rebuilds
        existing payslips each time, so corrections made before
        finalizing are picked up.
        """
        if self.status not in ('draft', 'computed'):
            raise ValidationError(
                "Can only compute a draft or already-computed run.")

        from django.contrib.auth import get_user_model
        User = get_user_model()
        as_of = as_of or self.period.pay_date
        staff_queryset = staff_queryset or User.objects.filter(
            is_staff=True, is_active=True)

        self.payslips.all().delete()

        for staff in staff_queryset:
            compensation = StaffCompensation.active_for(staff, as_of)
            if not compensation:
                continue
            payslip = Payslip.objects.create(
                run=self, staff=staff, compensation=compensation,
            )
            payslip.calculate(as_of=as_of)

        self.status = 'computed'
        self.save()

    def approve(self, by_user):
        if self.status != 'computed':
            return
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def finalize(self):
        if self.status != 'approved':
            return
        self.status = 'finalized'
        self.save()


class Payslip(BaseModelMixin):
    """One staff member's payslip within a PayrollRun."""

    run = models.ForeignKey(
        'PayrollRun',
        on_delete=models.CASCADE,
        related_name='payslips'
    )

    staff = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='payslips'
    )

    compensation = models.ForeignKey(
        'StaffCompensation',
        on_delete=models.PROTECT,
        related_name='payslips'
    )

    gross_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    taxable_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    total_statutory_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    total_voluntary_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    paye = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    net_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    total_employer_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="gross_pay plus employer-side statutory contributions "
        "(NSSF/AHL matching) — the institution's actual cost, "
        "distinct from net_pay.",
    )

    class Meta:
        unique_together = ('run', 'staff')
        ordering = ['staff']
        verbose_name = "Payslip"
        verbose_name_plural = "Payslips"

    def __str__(self):
        return f"{self.staff} — {self.run.period} — net KES {self.net_pay}"

    def calculate(self, as_of=None):
        """
        (Re)builds this payslip's PayslipLines and summary totals from the
        staff member's current compensation, active allowances, active
        StatutoryRate/PayeTaxBand/PayeRelief data, and any active
        StaffDeductionMandate rows. Idempotent — clears prior lines first.
        """
        as_of = as_of or self.run.period.pay_date
        self.lines.all().delete()

        basic = self.compensation.basic_salary
        PayslipLine.objects.create(
            payslip=self, line_type='earning', category='basic',
            description="Basic Salary", amount=basic,
        )

        gross = basic
        taxable_gross = basic  # basic salary is always taxable

        for allowance in SalaryAllowance.active_for(self.staff, as_of):
            PayslipLine.objects.create(
                payslip=self, line_type='earning', category='allowance',
                description=allowance.get_category_display(), amount=allowance.amount,
            )
            gross += allowance.amount
            if allowance.is_taxable:
                taxable_gross += allowance.amount

        statutory_total = Decimal('0.00')
        pre_paye_deductions = Decimal('0.00')
        employer_cost_addition = Decimal('0.00')

        for deduction_type in StatutoryDeductionType.objects.filter(
            is_active=True
        ).exclude(code='paye'):
            rate = StatutoryRate.active_for(deduction_type.code, as_of)
            if not rate:
                continue

            employee_amount = rate.compute_employee_amount(gross)
            if employee_amount > 0:
                PayslipLine.objects.create(
                    payslip=self, line_type='deduction', category='statutory_employee',
                    description=deduction_type.name, amount=employee_amount,
                    statutory_deduction_type=deduction_type,
                )
                statutory_total += employee_amount
                if deduction_type.is_allowable_before_paye:
                    pre_paye_deductions += employee_amount

            if deduction_type.is_employer_matched:
                employer_amount = rate.compute_employer_amount(gross)
                if employer_amount > 0:
                    PayslipLine.objects.create(
                        payslip=self, line_type='deduction', category='statutory_employer',
                        description=f"{deduction_type.name} (Employer)", amount=employer_amount,
                        statutory_deduction_type=deduction_type, is_employer_contribution=True,
                    )
                    employer_cost_addition += employer_amount

        taxable_pay = max(Decimal('0.00'), taxable_gross - pre_paye_deductions)
        paye_before_relief = PayeTaxBand.calculate_tax(taxable_pay, as_of)
        relief = PayeRelief.amount_as_of(as_of)
        paye = max(Decimal('0.00'), paye_before_relief - relief)

        if paye > 0:
            paye_type = StatutoryDeductionType.objects.filter(
                code='paye').first()
            PayslipLine.objects.create(
                payslip=self, line_type='deduction', category='paye',
                description="PAYE (net of personal relief)", amount=paye,
                statutory_deduction_type=paye_type,
            )

        voluntary_total = Decimal('0.00')
        for mandate in StaffDeductionMandate.active_for(self.staff, as_of):
            PayslipLine.objects.create(
                payslip=self, line_type='deduction', category='voluntary',
                description=mandate.description or mandate.get_category_display(),
                amount=mandate.amount, deduction_mandate=mandate,
            )
            voluntary_total += mandate.amount

        self.gross_pay = gross
        self.taxable_pay = taxable_pay
        self.total_statutory_deductions = statutory_total
        self.paye = paye
        self.total_voluntary_deductions = voluntary_total
        self.net_pay = gross - statutory_total - paye - voluntary_total
        self.total_employer_cost = gross + employer_cost_addition
        self.save()


class PayslipLine(BaseModelMixin):
    """One itemised earning or deduction line on a Payslip."""

    LINE_TYPE_CHOICES = [
        ('earning',   'Earning'),
        ('deduction', 'Deduction'),
    ]
    CATEGORY_CHOICES = [
        ('basic',               'Basic Salary'),
        ('allowance',           'Allowance'),
        ('statutory_employee',  'Statutory Deduction — Employee'),
        ('statutory_employer',  'Statutory Contribution — Employer'),
        ('paye',                'PAYE'),
        ('voluntary',           'Voluntary Deduction'),
    ]

    payslip = models.ForeignKey(
        'Payslip',
        on_delete=models.CASCADE,
        related_name='lines'
    )
    line_type = models.CharField(max_length=10, choices=LINE_TYPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    is_employer_contribution = models.BooleanField(
        default=False,
        help_text="True for the employer-matched portion of a statutory "
        "deduction — doesn't reduce net_pay, but counts toward "
        "total_employer_cost.",
    )

    statutory_deduction_type = models.ForeignKey(
        'StatutoryDeductionType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payslip_lines',
    )
    deduction_mandate = models.ForeignKey(
        'StaffDeductionMandate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payslip_lines',
    )

    class Meta:
        ordering = ['payslip', 'line_type', 'category']
        verbose_name = "Payslip Line"
        verbose_name_plural = "Payslip Lines"

    def __str__(self):
        return f"{self.description} — KES {self.amount}"


# ─────────────────────────────────────────────────────────────────────────────
# Remittance compliance
# ─────────────────────────────────────────────────────────────────────────────

class StatutoryRemittance(BaseModelMixin):
    """
    Tracks the actual monthly remittance of withheld statutory deductions
    to the relevant authority — a compliance obligation distinct from the
    payroll run itself, due by the 9th of the following month. Mirrors
    RegulatoryReport's pattern (see compliance.py) for the same reason:
    it's a deadline-bearing filing obligation, not just a ledger entry.
    """

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('remitted', 'Remitted'),
    ]

    period = models.ForeignKey(
        'PayrollPeriod',
        on_delete=models.PROTECT,
        related_name='remittances'
    )
    deduction_type = models.ForeignKey(
        'StatutoryDeductionType',
        on_delete=models.PROTECT,
        related_name='remittances'
    )

    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    remitted_date = models.DateField(null=True, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True, default="")
    remitted_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='statutory_remittances_processed',
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('period', 'deduction_type')
        ordering = ['-period']
        verbose_name = "Statutory Remittance"
        verbose_name_plural = "Statutory Remittances"

    def __str__(self):
        return f"{self.deduction_type.name} — {self.period} — KES {self.amount_due} [{self.get_status_display()}]"

    @property
    def is_overdue(self):
        return self.status == 'pending' and timezone.now().date() > self.period.remittance_due_date

    def mark_remitted(self, by_user, receipt_number="", remitted_date=None):
        self.status = 'remitted'
        self.remitted_by = by_user
        self.remitted_date = remitted_date or timezone.now().date()
        self.receipt_number = receipt_number
        self.save()

    @classmethod
    def generate_for_run(cls, payroll_run):
        """
        Rolls up a finalized run's PayslipLine amounts (employee + employer
        sides, excluding voluntary deductions) per StatutoryDeductionType
        into one StatutoryRemittance per authority for the period.
        """
        if payroll_run.status not in ('finalized', 'paid'):
            raise ValidationError(
                "Can only generate remittances for a finalized payroll run."
            )

        lines = PayslipLine.objects.filter(
            payslip__run=payroll_run,
            line_type='deduction',
            statutory_deduction_type__isnull=False,
        ).select_related('statutory_deduction_type')

        totals = {}
        for line in lines:
            key = line.statutory_deduction_type
            totals[key] = totals.get(key, Decimal('0.00')) + line.amount

        created = []
        for deduction_type, amount in totals.items():
            remittance, _ = cls.objects.get_or_create(
                period=payroll_run.period, deduction_type=deduction_type,
                defaults={'amount_due': amount},
            )
            created.append(remittance)

        return created
