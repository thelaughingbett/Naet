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
Institutional budgeting — Schools, Departments, and non-academic
administrative units (Registrar, ICT, Estates, Library, Finance, Student
Affairs, etc.) all getting a real, line-item, multi-category budget
envelope, not just the narrower per-Department procurement encumbrance
DepartmentBudget (procurement.py) tracks.

Relationship to DepartmentBudget: deliberately NOT a replacement.
DepartmentBudget stays the simple, Department-only, procurement-only path
for installations that don't need more. CostCentre/Budget/BudgetLine here
is the fuller path — it can represent a School, a Department, or an
administrative unit with no Department record at all, breaks the envelope
into categories (Personnel/Operating/Capital/...), and has a formal
submit → approve → active → close lifecycle plus an audited revision
(virement) trail for mid-year reallocations. An institution adopting this
module populates the new `cost_centre`/`budget_category` fields added
below going forward; existing DepartmentBudget usage is untouched.

To avoid double-counting the same procurement spend against two different
BudgetLine categories (e.g. 'operating' and 'capital' both existing for
one cost centre), committed/spent amounts are computed per BudgetCategory
by filtering PurchaseOrderLine/VendorInvoiceLine on an explicit
budget_category tag (added additively to procurement.py below) — not by a
blanket per-cost-centre total.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


class CostCentre(BaseModelMixin):
    """
    A budget-holding unit. Exactly one of `school`/`department` is set
    when centre_type is 'school'/'department'; neither is set for a
    free-standing administrative unit that has no corresponding academic
    model at all (there's no 'AdministrativeUnit' table elsewhere in this
    schema — this is deliberately the first place one gets named).
    """

    CENTRE_TYPE_CHOICES = [
        ('school',               'School'),
        ('department',           'Academic Department'),
        ('administrative_unit',  'Administrative / Support Unit'),
    ]

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="e.g. 'CC-001'."
    )
    centre_type = models.CharField(max_length=20, choices=CENTRE_TYPE_CHOICES)

    school = models.ForeignKey(
        'School',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cost_centres',
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cost_centres',
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text="For roll-up reporting — e.g. a Department cost centre's "
        "parent is its School's cost centre.",
    )

    head = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cost_centres_headed',
        help_text="The budget holder/accounting officer accountable for this centre.",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = "Cost Centre"
        verbose_name_plural = "Cost Centres"

    def __str__(self):
        return f"{self.code} — {self.name}"

    def clean(self):
        super().clean()

        if self.centre_type == 'school':
            if not self.school_id:
                raise ValidationError(
                    {'school': "Required when centre_type='school'."})
            if self.department_id:
                raise ValidationError(
                    {'department': "Must be blank when centre_type='school'."})

        elif self.centre_type == 'department':
            if not self.department_id:
                raise ValidationError(
                    {'department': "Required when centre_type='department'."})
            if self.school_id:
                raise ValidationError(
                    {'school': "Must be blank when centre_type='department'."})

        elif self.centre_type == 'administrative_unit':
            if self.school_id or self.department_id:
                raise ValidationError(
                    "An administrative unit cost centre shouldn't reference "
                    "a School or Department — it stands on its own."
                )

    @property
    def descendants(self):
        """All child cost centres, recursively, for roll-up reporting."""
        result = []
        for child in self.children.all():
            result.append(child)
            result.extend(child.descendants)
        return result


class BudgetCategory(BaseModelMixin):
    """
    A spending category a BudgetLine is allocated against. 'personnel' and
    the procurement-fed categories ('operating', 'capital') get automatic
    committed/spent tracking (see BudgetLine); others are informational
    envelopes finance tracks manually unless/until they're also wired to
    a spend source.
    """

    CODE_CHOICES = [
        ('personnel',   'Personnel Costs'),
        ('operating',   'Operating Expenses'),
        ('capital',     'Capital Expenditure'),
        ('travel',      'Travel & Logistics'),
        ('utilities',   'Utilities'),
        ('maintenance', 'Maintenance & Repairs'),
        ('other',       'Other'),
    ]

    code = models.CharField(
        max_length=20,
        choices=CODE_CHOICES,
        unique=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['code']
        verbose_name = "Budget Category"
        verbose_name_plural = "Budget Categories"

    def __str__(self):
        return self.name


class Budget(BaseModelMixin):
    """
    A CostCentre's approved envelope for a fiscal year. The envelope
    itself is a formal, approved document (draft → submitted → approved →
    active → closed) — changes to it once active go through BudgetRevision,
    not a direct edit to a BudgetLine's allocated_amount.
    """

    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('submitted', 'Submitted for Approval'),
        ('approved',  'Approved'),
        ('active',    'Active'),
        ('closed',    'Closed'),
        ('rejected',  'Rejected'),
    ]

    cost_centre = models.ForeignKey(
        'CostCentre',
        on_delete=models.PROTECT,
        related_name='budgets'
    )

    fiscal_year = models.ForeignKey(
        'FiscalYear',
        on_delete=models.PROTECT,
        related_name='budgets'
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    prepared_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budgets_prepared',
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budgets_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ('cost_centre', 'fiscal_year')
        ordering = ['-fiscal_year', 'cost_centre']
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"

    def __str__(self):
        return f"{self.cost_centre} — {self.fiscal_year} [{self.get_status_display()}]"

    @property
    def total_allocated(self):
        total = self.lines.aggregate(
            total=models.Sum('allocated_amount'))['total']
        return total or Decimal('0.00')

    @property
    def total_committed(self):
        return sum((line.committed_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_spent(self):
        return sum((line.spent_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_available(self):
        return self.total_allocated - self.total_committed - self.total_spent

    def submit(self, by_user):
        if self.status != 'draft':
            return
        if not self.lines.exists():
            raise ValidationError("Cannot submit a budget with no line items.")
        self.status = 'submitted'
        self.prepared_by = self.prepared_by or by_user
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, by_user):
        if self.status != 'submitted':
            return
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, by_user, reason):
        if self.status != 'submitted':
            return
        self.status = 'rejected'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def activate(self):
        if self.status != 'approved':
            return
        self.status = 'active'
        self.save()

    def close(self):
        if self.status != 'active':
            return
        self.status = 'closed'
        self.save()

    @classmethod
    def consolidated_totals(cls, cost_centre, fiscal_year):
        """
        Rolls up this cost centre's own approved/active budget plus every
        descendant cost centre's — e.g. a School's total including all
        its Departments — for the same fiscal year.
        """
        centres = [cost_centre] + cost_centre.descendants
        budgets = cls.objects.filter(
            cost_centre__in=centres, fiscal_year=fiscal_year,
            status__in=['approved', 'active', 'closed'],
        )

        totals = {'allocated': Decimal('0.00'), 'committed': Decimal(
            '0.00'), 'spent': Decimal('0.00')}
        for budget in budgets:
            totals['allocated'] += budget.total_allocated
            totals['committed'] += budget.total_committed
            totals['spent'] += budget.total_spent

        totals['available'] = totals['allocated'] - \
            totals['committed'] - totals['spent']
        return totals


class BudgetLine(BaseModelMixin):
    """
    One category's allocation within a Budget. committed_amount/
    spent_amount are computed, not stored — 'personnel' pulls from
    finalized/paid PayrollRuns tagged with this cost centre;
    'operating'/'capital' (or any category) pull from PurchaseOrderLine/
    VendorInvoiceLine rows explicitly tagged with this BudgetCategory, so
    two categories never double-count the same procurement spend.
    """

    budget = models.ForeignKey(
        'Budget',
        on_delete=models.CASCADE,
        related_name='lines'
    )
    category = models.ForeignKey(
        'BudgetCategory',
        on_delete=models.PROTECT,
        related_name='budget_lines'
    )

    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ('budget', 'category')
        ordering = ['budget', 'category']
        verbose_name = "Budget Line"
        verbose_name_plural = "Budget Lines"

    def __str__(self):
        return f"{self.budget} — {self.category} — KES {self.allocated_amount}"

    @property
    def committed_amount(self):
        if self.category.code == 'personnel':
            # payroll isn't encumbered ahead of time — see spent_amount
            return Decimal('0.00')
        return self._procurement_committed()

    @property
    def spent_amount(self):
        if self.category.code == 'personnel':
            return self._personnel_spent()
        return self._procurement_spent()

    @property
    def available_amount(self):
        return self.allocated_amount - self.committed_amount - self.spent_amount

    def _procurement_committed(self):
        from ..procurement import PurchaseOrderLine
        lines = PurchaseOrderLine.objects.filter(
            po__cost_centre=self.budget.cost_centre,
            po__fiscal_year=self.budget.fiscal_year,
            po__status__in=['sent', 'partially_received', 'received'],
            budget_category=self.category,
        )
        total = Decimal('0.00')
        for line in lines:
            total += line.uninvoiced_committed_amount
        return total

    def _procurement_spent(self):
        from ..procurement import VendorInvoiceLine
        total = VendorInvoiceLine.objects.filter(
            invoice__po__cost_centre=self.budget.cost_centre,
            invoice__po__fiscal_year=self.budget.fiscal_year,
            invoice__status__in=['approved', 'paid'],
            budget_category=self.category,
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    def _personnel_spent(self):
        from .payroll import Payslip
        fy = self.budget.fiscal_year
        total = Payslip.objects.filter(
            compensation__cost_centre=self.budget.cost_centre,
            run__status__in=['finalized', 'paid'],
            run__period__pay_date__gte=fy.start_date,
            run__period__pay_date__lte=fy.end_date,
        ).aggregate(total=models.Sum('total_employer_cost'))['total']
        return total or Decimal('0.00')


class BudgetRevision(BaseModelMixin):
    """
    A formal, audited reallocation of funds — either between two
    BudgetLines within the same Budget (virement), or a top-up/cut to a
    single line. Mid-year budget changes with no recorded trail are a
    classic audit finding, so this is its own approved record, not a
    silent edit to BudgetLine.allocated_amount — the actual reallocation
    only happens inside approve().
    """

    REVISION_TYPE_CHOICES = [
        ('virement', 'Virement — Move Between Lines'),
        ('topup',    'Top-Up — Additional Allocation'),
        ('cut',      'Cut — Reduced Allocation'),
    ]

    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]

    budget = models.ForeignKey(
        'Budget',
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    revision_type = models.CharField(
        max_length=10,
        choices=REVISION_TYPE_CHOICES
    )

    from_line = models.ForeignKey(
        'BudgetLine',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='revisions_out',
        help_text="Required for 'virement' and 'cut' — the line funds move from / are reduced on.",
    )
    to_line = models.ForeignKey(
        'BudgetLine',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='revisions_in',
        help_text="Required for 'virement' and 'topup' — the line funds move to / are increased on.",
    )

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    justification = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    requested_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_revisions_requested',
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_revisions_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Budget Revision"
        verbose_name_plural = "Budget Revisions"

    def __str__(self):
        return f"{self.get_revision_type_display()} — {self.budget} — KES {self.amount} [{self.get_status_display()}]"

    def clean(self):
        super().clean()

        if self.revision_type == 'virement':
            if not self.from_line_id or not self.to_line_id:
                raise ValidationError(
                    "Virement requires both a from_line and a to_line.")
            if self.from_line_id == self.to_line_id:
                raise ValidationError(
                    "from_line and to_line must be different lines.")
        elif self.revision_type == 'topup':
            if not self.to_line_id:
                raise ValidationError(
                    {'to_line': "Top-up requires a target line."})
        elif self.revision_type == 'cut':
            if not self.from_line_id:
                raise ValidationError(
                    {'from_line': "Cut requires a source line."})

        for line in (self.from_line, self.to_line):
            if line and self.budget_id and line.budget_id != self.budget_id:
                raise ValidationError(
                    f"{line} does not belong to this revision's budget."
                )

    def submit(self):
        if self.status != 'draft':
            return
        self.status = 'submitted'
        self.save()

    def reject(self, by_user, reason=""):
        if self.status != 'submitted':
            return
        self.status = 'rejected'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        if reason:
            self.justification = f"{self.justification}\n\nRejected: {reason}".strip(
            )
        self.save()

    def approve(self, by_user):
        """Applies the actual reallocation, then marks this revision approved."""
        if self.status != 'submitted':
            return

        if self.revision_type in ('virement', 'cut'):
            if self.from_line.available_amount < self.amount:
                raise ValidationError(
                    f"Cannot move/cut KES {self.amount} from {self.from_line} — "
                    f"only KES {self.from_line.available_amount} is available."
                )
            self.from_line.allocated_amount -= self.amount
            self.from_line.save()

        if self.revision_type in ('virement', 'topup'):
            self.to_line.allocated_amount += self.amount
            self.to_line.save()

        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()
