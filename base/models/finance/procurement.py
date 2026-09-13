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
Accounts payable / procurement — institution-level vendor spend, distinct
from ClubTransaction (club-level) and StudentFeeAccount/Payment (student
receivables). Workflow:

    PurchaseRequisition → PurchaseOrder → GoodsReceipt → VendorInvoice → VendorPayment

Budget is *encumbered* the moment a PurchaseOrder is sent (DepartmentBudget.
committed_amount), not just when an invoice lands — standard institutional/
public-sector practice, distinct from how a purely commercial AP module
would track only realised spend. See DepartmentBudget for the accounting.

GL integration (JournalEntry.for_vendor_invoice() / for_vendor_payment())
lives in ledger.py, not here, following the same pattern as the student-fee
side (for_payment()/for_refund()).
"""

import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


class Vendor(BaseModelMixin):
    """A supplier of goods, works, services, or consultancy to the institution."""

    CATEGORY_CHOICES = [
        ('goods',       'Goods'),
        ('services',    'Services'),
        ('works',       'Works / Construction'),
        ('consultancy', 'Consultancy'),
        ('utilities',   'Utilities'),
        ('other',       'Other'),
    ]

    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(
        max_length=15,
        choices=CATEGORY_CHOICES,
        default='goods'
    )

    tax_pin = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="KRA PIN."
    )

    registration_number = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )

    contact_person = models.CharField(
        max_length=150,
        blank=True,
        default=""
    )
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        default=""
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )
    bank_branch = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    is_active = models.BooleanField(default=True)
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ['name']
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.is_blacklisted and not self.blacklist_reason:
            raise ValidationError({
                'blacklist_reason': "A reason is required when blacklisting a vendor."
            })
        if self.is_blacklisted and self.is_active:
            raise ValidationError({
                'is_active': "A blacklisted vendor cannot remain active."
            })


class DepartmentBudget(BaseModelMixin):
    """
    A department's spending envelope for a fiscal year. Tracks committed
    (encumbered by open, uninvoiced POs) and spent (recognised via approved/
    paid invoices) separately — as invoices land against a PO, the amount
    moves out of 'committed' and into 'spent' rather than being counted in
    both, so available_amount never double-penalises the same PO twice.
    """

    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='budgets'
    )
    fiscal_year = models.ForeignKey(
        'FiscalYear',
        on_delete=models.PROTECT,
        related_name='department_budgets'
    )

    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ('department', 'fiscal_year')
        ordering = ['-fiscal_year', 'department']
        verbose_name = "Department Budget"
        verbose_name_plural = "Department Budgets"

    def __str__(self):
        return f"{self.department} — {self.fiscal_year}"

    @property
    def committed_amount(self):
        """
        Sum, across open POs for this department+fiscal_year, of each PO's
        total minus whatever's already been invoiced against it — i.e. the
        portion still only *promised*, not yet billed.
        """
        open_pos = PurchaseOrder.objects.filter(
            department=self.department,
            fiscal_year=self.fiscal_year,
            status__in=['sent', 'partially_received', 'received'],
        )
        total = Decimal('0.00')
        for po in open_pos:
            total += po.uninvoiced_committed_amount
        return total

    @property
    def spent_amount(self):
        """Sum of approved/paid vendor invoice line totals against POs
        for this department+fiscal_year — the recognised expense."""
        total = VendorInvoiceLine.objects.filter(
            invoice__po__department=self.department,
            invoice__po__fiscal_year=self.fiscal_year,
            invoice__status__in=['approved', 'paid'],
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def available_amount(self):
        return self.allocated_amount - self.committed_amount - self.spent_amount


# ─────────────────────────────────────────────────────────────────────────────
# Requisition
# ─────────────────────────────────────────────────────────────────────────────

class PurchaseRequisition(BaseModelMixin):
    """A department's internal request to procure something — the stage
    before a formal PurchaseOrder exists, and before any vendor is named."""

    STATUS_CHOICES = [
        ('draft',           'Draft'),
        ('submitted',       'Submitted'),
        ('approved',        'Approved'),
        ('rejected',        'Rejected'),
        ('converted_to_po', 'Converted to Purchase Order'),
        ('cancelled',       'Cancelled'),
    ]

    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='requisitions'
    )

    cost_centre = models.ForeignKey(
        'CostCentre',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions',
        help_text="Optional — set to feed the fuller Budget/BudgetLine "
        "system (budgeting.py) instead of/alongside DepartmentBudget.",
    )

    fiscal_year = models.ForeignKey(
        'FiscalYear',
        on_delete=models.PROTECT,
        related_name='requisitions'
    )

    requested_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions_made',
    )

    justification = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Purchase Requisition"
        verbose_name_plural = "Purchase Requisitions"

    def __str__(self):
        return f"Requisition — {self.department} — {self.fiscal_year} [{self.get_status_display()}]"

    @property
    def total_estimated_amount(self):
        total = self.lines.aggregate(
            total=models.Sum(models.F('quantity') *
                             models.F('estimated_unit_price'))
        )['total']
        return total or Decimal('0.00')

    def submit(self):
        if self.status != 'draft':
            return
        self.status = 'submitted'
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

    def convert_to_po(self, vendor, by_user):
        """
        Creates a draft PurchaseOrder pre-populated from this requisition's
        lines (the estimated unit price becomes the PO's starting
        unit_price — procurement should confirm actual vendor pricing
        before calling PurchaseOrder.send()). Marks this requisition
        'converted_to_po'.
        """
        if self.status != 'approved':
            raise ValidationError(
                "Only an approved requisition can be converted to a purchase order."
            )

        po = PurchaseOrder.objects.create(
            vendor=vendor,
            department=self.department,
            cost_centre=self.cost_centre,
            fiscal_year=self.fiscal_year,
            requisition=self,
            requested_by=self.requested_by,
        )
        for line in self.lines.all():
            PurchaseOrderLine.objects.create(
                po=po,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.estimated_unit_price,
                account=line.account,
                budget_category=line.budget_category,
            )

        self.status = 'converted_to_po'
        self.save()
        return po


class PurchaseRequisitionLine(BaseModelMixin):
    requisition = models.ForeignKey(
        'PurchaseRequisition',
        on_delete=models.CASCADE,
        related_name='lines'
    )

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='requisition_lines',
        help_text="The expense/asset account this line is expected to post "
        "to once invoiced — carried forward to the PO line on "
        "conversion.",
    )
    budget_category = models.ForeignKey(
        'BudgetCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisition_lines',
        help_text="Optional — which BudgetLine (budgeting.py) this should "
        "count against. Carried forward to the PO line on conversion.",
    )

    class Meta:
        ordering = ['requisition', 'created_at']
        verbose_name = "Requisition Line"
        verbose_name_plural = "Requisition Lines"

    def __str__(self):
        return f"{self.description} × {self.quantity} @ KES {self.estimated_unit_price}"

    @property
    def line_total(self):
        return self.quantity * self.estimated_unit_price


# ─────────────────────────────────────────────────────────────────────────────
# Purchase orders
# ─────────────────────────────────────────────────────────────────────────────

class PurchaseOrder(BaseModelMixin):
    """A formal, vendor-facing order — the point at which budget is
    encumbered (see DepartmentBudget.committed_amount)."""

    STATUS_CHOICES = [
        ('draft',              'Draft'),
        ('sent',               'Sent to Vendor'),
        ('partially_received', 'Partially Received'),
        ('received',           'Fully Received'),
        ('closed',             'Closed'),
        ('cancelled',          'Cancelled'),
    ]

    po_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True
    )

    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    cost_centre = models.ForeignKey(
        'CostCentre',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders',
        help_text="Optional — set to feed the fuller Budget/BudgetLine "
        "system (budgeting.py) instead of/alongside DepartmentBudget.",
    )
    fiscal_year = models.ForeignKey(
        'FiscalYear',
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    requisition = models.ForeignKey(
        'PurchaseRequisition', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_orders',
    )

    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    requested_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders_requested',
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        ordering = ['-order_date', '-created_at']
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"

    def __str__(self):
        return f"{self.po_number or 'DRAFT'} — {self.vendor} [{self.get_status_display()}]"

    @property
    def total_amount(self):
        total = self.lines.aggregate(
            total=models.Sum(models.F('quantity') * models.F('unit_price'))
        )['total']
        return total or Decimal('0.00')

    @property
    def invoiced_amount(self):
        """Sum of line amounts from invoices raised against this PO that
        have progressed past matching (matched/approved/paid)."""
        total = VendorInvoiceLine.objects.filter(
            invoice__po=self, invoice__status__in=[
                'matched', 'approved', 'paid']
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def uninvoiced_committed_amount(self):
        """The portion of this PO still only encumbered, not yet invoiced —
        what DepartmentBudget.committed_amount actually sums."""
        return max(Decimal('0.00'), self.total_amount - self.invoiced_amount)

    def _generate_po_number(self):
        year = self.order_date.year if self.order_date else timezone.now().year
        while True:
            candidate = f"LPO-{year}-{random.randint(0, 999999):06d}"
            if not PurchaseOrder.objects.filter(po_number=candidate).exists():
                return candidate

    def send(self, by_user):
        """
        Moves a draft PO to 'sent' — the point at which it commits
        (encumbers) budget. Blocks if it would push the department over
        its available budget for the fiscal year.
        """
        if self.status != 'draft':
            return
        if not self.lines.exists():
            raise ValidationError(
                "Cannot send a purchase order with no line items.")

        budget = DepartmentBudget.objects.filter(
            department=self.department, fiscal_year=self.fiscal_year
        ).first()
        if budget and self.total_amount > budget.available_amount:
            raise ValidationError(
                f"This PO (KES {self.total_amount}) exceeds {self.department}'s "
                f"available budget (KES {budget.available_amount}) for "
                f"{self.fiscal_year}."
            )

        if not self.po_number:
            self.po_number = self._generate_po_number()
        self.status = 'sent'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def refresh_receipt_status(self):
        """
        Call after recording GoodsReceiptLines against this PO to
        recompute whether it's now partially or fully received.
        """
        lines = list(self.lines.all())
        if not lines:
            return
        if all(line.is_fully_received for line in lines):
            self.status = 'received'
            self.save()
        elif any(line.quantity_received > 0 for line in lines):
            self.status = 'partially_received'
            self.save()

    def cancel(self, by_user, reason=""):
        if self.receipts.exists() or self.invoices.exists():
            raise ValidationError(
                "Cannot cancel a purchase order that already has receipts "
                "or invoices recorded against it."
            )
        self.status = 'cancelled'
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.save()


class PurchaseOrderLine(BaseModelMixin):
    po = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.CASCADE,
        related_name='lines'
    )

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='po_lines',
        help_text="The expense/asset account this line posts to when invoiced.",
    )
    budget_category = models.ForeignKey(
        'BudgetCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_lines',
        help_text="Optional — which BudgetLine (budgeting.py) this line's "
        "committed/spent amount should count against. Required "
        "for BudgetLine's automatic tracking to see this line at all.",
    )

    class Meta:
        ordering = ['po', 'created_at']
        verbose_name = "Purchase Order Line"
        verbose_name_plural = "Purchase Order Lines"

    def __str__(self):
        return f"{self.description} × {self.quantity} @ KES {self.unit_price}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def quantity_received(self):
        total = self.receipt_lines.aggregate(
            total=models.Sum('quantity_received'))['total']
        return total or Decimal('0.00')

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity

    @property
    def quantity_invoiced(self):
        total = self.invoice_lines.filter(
            invoice__status__in=['matched', 'approved', 'paid']
        ).aggregate(total=models.Sum('quantity'))['total']
        return total or Decimal('0.00')

    @property
    def invoiced_amount(self):
        """Sum of invoice line amounts billed against this specific PO
        line (as opposed to PurchaseOrder.invoiced_amount, which sums
        across the whole order) — what BudgetLine's per-category tracking
        actually needs, so two categories on the same PO never double-count."""
        total = self.invoice_lines.filter(
            invoice__status__in=['matched', 'approved', 'paid']
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def uninvoiced_committed_amount(self):
        return max(Decimal('0.00'), self.line_total - self.invoiced_amount)


# ─────────────────────────────────────────────────────────────────────────────
# Goods receipt
# ─────────────────────────────────────────────────────────────────────────────

class GoodsReceipt(BaseModelMixin):
    """A single delivery event against a PurchaseOrder — a PO can have
    several receipts if the vendor delivers in installments."""

    po = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.PROTECT,
        related_name='receipts'
    )

    received_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goods_receipts_recorded',
    )
    received_date = models.DateField(default=timezone.now)
    delivery_note_number = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-received_date']
        verbose_name = "Goods Receipt"
        verbose_name_plural = "Goods Receipts"

    def __str__(self):
        return f"Receipt — {self.po} — {self.received_date}"

    def clean(self):
        super().clean()
        if self.po_id and self.po.status not in ('sent', 'partially_received'):
            raise ValidationError(
                "Can only record a receipt against a PO that's been sent "
                "and isn't already fully received."
            )


class GoodsReceiptLine(BaseModelMixin):
    receipt = models.ForeignKey(
        'GoodsReceipt',
        on_delete=models.CASCADE,
        related_name='lines'
    )
    po_line = models.ForeignKey(
        'PurchaseOrderLine',
        on_delete=models.PROTECT,
        related_name='receipt_lines'
    )

    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    condition_notes = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="e.g. '2 units damaged in transit'.",
    )

    class Meta:
        ordering = ['receipt', 'created_at']
        verbose_name = "Goods Receipt Line"
        verbose_name_plural = "Goods Receipt Lines"

    def __str__(self):
        return f"{self.po_line.description} × {self.quantity_received} received"

    def clean(self):
        super().clean()
        if self.po_line_id and self.quantity_received is not None:
            already_received = self.po_line.quantity_received
            if self._state.adding:
                projected = already_received + self.quantity_received
            else:
                # editing an existing line — exclude its own prior amount
                # from the running total before adding the new value back
                projected = already_received
            if projected > self.po_line.quantity:
                raise ValidationError({
                    'quantity_received': "This would receive more than was "
                    "ordered on this PO line."
                })


# ─────────────────────────────────────────────────────────────────────────────
# Vendor invoices
# ─────────────────────────────────────────────────────────────────────────────

class VendorInvoice(BaseModelMixin):
    """
    A vendor's bill. `po` is optional — non-PO invoices (utilities,
    subscriptions, one-off services) can be recorded directly. Payability
    is gated by perform_three_way_match(): a PO-backed invoice must match
    quantity received and expected price before it can be approved; a
    non-PO invoice has nothing to check against and matches vacuously.
    """

    STATUS_CHOICES = [
        ('pending_match', 'Pending Match'),
        ('matched',        'Matched'),
        ('disputed',       'Disputed'),
        ('approved',       'Approved for Payment'),
        ('paid',           'Paid'),
        ('cancelled',      'Cancelled'),
    ]

    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    po = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoices',
        help_text="Optional — leave blank for non-PO invoices "
        "(utilities, subscriptions, etc.).",
    )

    invoice_number = models.CharField(
        max_length=100,
        help_text="The vendor's own invoice number."
    )
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending_match',
        db_index=True
    )
    dispute_reason = models.TextField(blank=True, default="")

    matched_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_invoices_matched',
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_invoices_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('vendor', 'invoice_number')
        ordering = ['-invoice_date']
        verbose_name = "Vendor Invoice"
        verbose_name_plural = "Vendor Invoices"

    def __str__(self):
        return f"{self.vendor} — {self.invoice_number} [{self.get_status_display()}]"

    @property
    def total_amount(self):
        total = self.lines.aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def amount_paid(self):
        total = self.payment_allocations.filter(
            payment__status='completed'
        ).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def is_cleared(self):
        return self.balance <= 0

    def perform_three_way_match(self, tolerance_percent=Decimal('2.00')):
        """
        For each line tied to a PO line: checks cumulative invoiced
        quantity (across all matched/approved/paid invoices against that
        PO line, plus this line) doesn't exceed quantity received, and
        that the line amount is within `tolerance_percent` of
        po_line.unit_price × quantity. Lines with no po_line (non-PO
        invoices) are skipped, so an invoice with only such lines matches
        vacuously. Sets status to 'matched' or 'disputed' accordingly.
        """
        mismatches = []

        for line in self.lines.select_related('po_line'):
            if not line.po_line_id:
                continue

            po_line = line.po_line
            line_qty = line.quantity or Decimal('1')
            cumulative_invoiced = po_line.quantity_invoiced + line_qty

            if cumulative_invoiced > po_line.quantity_received:
                mismatches.append(
                    f"{line.description}: cumulative invoiced quantity "
                    f"({cumulative_invoiced}) exceeds quantity received "
                    f"({po_line.quantity_received})"
                )
                continue

            expected = po_line.unit_price * line_qty
            if expected > 0:
                variance = abs(line.amount - expected) / expected * 100
                if variance > tolerance_percent:
                    mismatches.append(
                        f"{line.description}: amount KES {line.amount} vs "
                        f"expected KES {expected} ({variance:.1f}% variance)"
                    )

        if mismatches:
            self.status = 'disputed'
            self.dispute_reason = "; ".join(mismatches)
        else:
            self.status = 'matched'
            self.dispute_reason = ""
            self.matched_at = timezone.now()

        self.save()
        return not mismatches

    def approve(self, by_user):
        if self.status != 'matched':
            raise ValidationError(
                "Only a matched invoice can be approved for payment — run "
                "perform_three_way_match() first."
            )
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def cancel(self, reason=""):
        if self.status == 'paid':
            raise ValidationError(
                "Cannot cancel an invoice that's already been paid.")
        self.status = 'cancelled'
        if reason:
            self.dispute_reason = reason
        self.save()


class VendorInvoiceLine(BaseModelMixin):
    invoice = models.ForeignKey(
        'VendorInvoice',
        on_delete=models.CASCADE,
        related_name='lines'
    )
    po_line = models.ForeignKey(
        'PurchaseOrderLine',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoice_lines',
        help_text="Link to the PO line this is billing against, for "
        "three-way matching. Leave blank for non-PO invoices.",
    )

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank for non-PO/non-quantity lines (e.g. a "
        "flat-fee utility charge).",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoice_lines',
        help_text="Expense/asset account this line posts to. Defaults to "
        "the linked PO line's account if left blank.",
    )
    budget_category = models.ForeignKey(
        'BudgetCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_lines',
        help_text="Which BudgetLine (budgeting.py) this counts as spent "
        "against. Defaults to the linked PO line's category if left blank.",
    )

    class Meta:
        ordering = ['invoice', 'created_at']
        verbose_name = "Vendor Invoice Line"
        verbose_name_plural = "Vendor Invoice Lines"

    def __str__(self):
        return f"{self.description} — KES {self.amount}"

    def clean(self):
        super().clean()
        if not self.account_id and self.po_line_id:
            self.account = self.po_line.account
        if not self.account_id:
            raise ValidationError({
                'account': "An account is required — either set directly, "
                           "or via a linked PO line."
            })
        if not self.budget_category_id and self.po_line_id:
            self.budget_category = self.po_line.budget_category


# ─────────────────────────────────────────────────────────────────────────────
# Vendor payments
# ─────────────────────────────────────────────────────────────────────────────

class VendorPayment(BaseModelMixin):
    """
    A payment run to a vendor — can settle several invoices at once via
    VendorPaymentAllocation, matching how AP payment runs actually work
    (one bank transfer/cheque covering multiple outstanding invoices).
    """

    METHOD_CHOICES = [
        ("bank",   "Bank Transfer"),
        ("cheque", "Cheque"),
        ("mpesa",  "M-Pesa"),
        ("cash",   "Cash"),
    ]

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.PROTECT,
        related_name='payments'
    )

    invoices = models.ManyToManyField(
        'VendorInvoice',
        through='VendorPaymentAllocation',
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Cheque number / bank transfer reference.",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    requested_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_payments_requested',
    )

    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_payments_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Vendor Payment"
        verbose_name_plural = "Vendor Payments"

    def __str__(self):
        return f"Payment — {self.vendor} — KES {self.amount} [{self.get_status_display()}]"

    @property
    def allocated_total(self):
        total = self.allocations.aggregate(
            total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def is_fully_allocated(self):
        return self.allocated_total == self.amount

    def approve(self, by_user):
        if self.status != 'pending':
            return
        self.status = 'approved'
        self.approved_by = by_user
        self.approved_at = timezone.now()
        self.save()

    def confirm(self, transaction_ref=None):
        """
        Finalises the payment — requires every allocation to already be in
        place and to sum exactly to `amount`. Marks any fully-covered
        allocated invoice as 'paid'.
        """
        if self.status not in ('pending', 'approved'):
            return
        if not self.is_fully_allocated:
            raise ValidationError(
                f"Payment amount KES {self.amount} doesn't match the "
                f"allocated total KES {self.allocated_total}."
            )

        self.status = 'completed'
        if transaction_ref:
            self.reference = transaction_ref
        self.paid_at = timezone.now()
        self.save()

        for allocation in self.allocations.select_related('invoice'):
            invoice = allocation.invoice
            if invoice.status == 'approved' and invoice.is_cleared:
                invoice.status = 'paid'
                invoice.save()


class VendorPaymentAllocation(BaseModelMixin):
    """How much of a VendorPayment goes toward a specific VendorInvoice."""

    payment = models.ForeignKey(
        'VendorPayment',
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    invoice = models.ForeignKey(
        'VendorInvoice',
        on_delete=models.PROTECT,
        related_name='payment_allocations'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('payment', 'invoice')
        ordering = ['payment', 'created_at']
        verbose_name = "Vendor Payment Allocation"
        verbose_name_plural = "Vendor Payment Allocations"

    def __str__(self):
        return f"{self.payment} → {self.invoice} — KES {self.amount}"

    def clean(self):
        super().clean()
        if self.invoice_id and self.amount is not None:
            if self.amount > self.invoice.balance:
                raise ValidationError({
                    'amount': f"Allocation exceeds the invoice's outstanding "
                    f"balance (KES {self.invoice.balance})."
                })
