# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from simple_history.models import HistoricalRecords

from ..base import BaseModelMixin


class ClubBudget(BaseModelMixin):
    """
    A club's approved financial envelope for a given Session — "Club
    Budget & Expenses" in the Club Management sidebar. Actual income and
    spend against it is tracked via ClubTransaction below.
    """

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="budgets",
    )

    session = models.ForeignKey(
        "Session",
        on_delete=models.PROTECT,
        related_name="club_budgets",
    )

    allocated_amount = models.PositiveIntegerField(
        default=0,
        help_text="KES. Approved allocation for this club for this session "
        "(e.g. from a Student Council/Dean of Students grant).",
    )

    notes = models.TextField(blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        unique_together = ("club", "session")
        verbose_name = "Club Budget"
        verbose_name_plural = "Club Budgets"

    def __str__(self):
        return f"{self.club} — {self.session} budget"

    @property
    def total_income(self):
        total = self.transactions.filter(
            transaction_type="income", status="approved"
        ).aggregate(total=models.Sum("amount"))["total"]
        return total or 0

    @property
    def total_expenses(self):
        total = self.transactions.filter(
            transaction_type="expense", status="approved"
        ).aggregate(total=models.Sum("amount"))["total"]
        return total or 0

    @property
    def balance(self):
        return self.allocated_amount + self.total_income - self.total_expenses


class ClubTransaction(BaseModelMixin):
    """
    A single income or expense line item for a club — feeds the "Club
    Budget & Expenses" view. Tied to a ClubBudget where one exists for the
    session; a club can still log transactions without a formal budget
    (e.g. informal fundraiser proceeds), so `budget` is optional.
    """

    TRANSACTION_TYPE_CHOICES = [
        ("income",  "Income"),
        ("expense", "Expense"),
    ]

    CATEGORY_CHOICES = [
        ("dues",         "Membership Dues"),
        ("fundraiser",   "Fundraiser"),
        ("sponsorship",  "Sponsorship"),
        ("grant",        "Institutional Grant"),
        ("event_cost",   "Event Cost"),
        ("equipment",    "Equipment / Supplies"),
        ("transport",    "Transport"),
        ("refreshments", "Refreshments"),
        ("other",        "Other"),
    ]

    STATUS_CHOICES = [
        ("draft",    "Draft"),
        ("pending",  "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    club = models.ForeignKey(
        "Club",
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    budget = models.ForeignKey(
        "ClubBudget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )

    amount = models.PositiveIntegerField(help_text="KES")
    description = models.CharField(max_length=255)

    receipt = models.FileField(
        upload_to="club_transactions/",
        null=True,
        blank=True,
    )

    # Typically the club's treasurer, but any exec member can log a
    # transaction for review.
    recorded_by = models.ForeignKey(
        "ClubMembership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_transactions",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="club_transactions_reviewed",
        limit_choices_to={"is_staff": True},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    transacted_at = models.DateField(default=timezone.now)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-transacted_at"]
        verbose_name = "Club Transaction"
        verbose_name_plural = "Club Transactions"

    def __str__(self):
        sign = "+" if self.transaction_type == "income" else "-"
        return f"{self.club} — {sign}KES {self.amount} ({self.description})"

    def clean(self):
        super().clean()

        if self.budget_id and self.budget.club_id != self.club_id:
            raise ValidationError({
                "budget": "This budget belongs to a different club."
            })

        if self.recorded_by_id and self.recorded_by.club_id != self.club_id:
            raise ValidationError({
                "recorded_by": "The recorder must be a member of this club."
            })

    def approve(self, by_user):
        if self.status != "pending":
            return
        self.status = "approved"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, by_user):
        if self.status != "pending":
            return
        self.status = "rejected"
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save()
