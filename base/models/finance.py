# Copyright 2026 Emmanuel Kipng'eno

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.core.exceptions import ValidationError
from .base import BaseModelMixin

from django.db import models

from simple_history.models import HistoricalRecords

import datetime


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

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    history = HistoricalRecords()

    class Meta:
        unique_together = ('student', 'fee_structure')

    @property
    def balance(self):
        return self.amount_billed - self.amount_paid

    @property
    def is_cleared(self):
        return self.balance <= 0

    @property
    def amount_billed(self):
        return self.fee_structure.total_amount

    @property
    def days_remaining(self):
        # Subtracts today's date from the due date

        delta = self.fee_structure.session.end_date - \
            datetime.timedelta(days=14)
        return delta

    def __str__(self):
        return f"{self.student.registration_number} - {self.fee_structure} - balance: {self.balance}"


class OverDraft(BaseModelMixin):

    STATUS_CHOICES = [
        ('pending', 'Pending'),      # just recorded, not yet processed
        ('carried', 'Carried Over'),  # applied to next session
        ('refunded', 'Refunded'),    # refunded to student
    ]

    account = models.ForeignKey(
        "StudentFeeAccount",
        on_delete=models.PROTECT,
        related_name='overdrafts'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction = models.ForeignKey(
        "Payment",
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    applied_to = models.ForeignKey(
        'StudentFeeAccount',
        on_delete=models.PROTECT,
        related_name='credits',
        null=True,
        blank=True
    )  # points to the next session account if carried over

    history = HistoricalRecords()

    def process(self):
        from django.utils import timezone

        student = self.account.student

        # find next active session account for this student
        next_account = StudentFeeAccount.objects.filter(
            student=student,
        ).exclude(
            record_id=self.account.record_id
        ).order_by('created_at').last()

        if next_account and not next_account.is_cleared:
            # carry forward
            next_account.amount_paid += self.amount
            next_account.save()

            self.status = 'carried'
            self.applied_to = next_account
            self.save()

        else:
            # no active next session — flag for refund
            self.status = 'refunded'
            self.save()
            # TODO: trigger refund notification/process here


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
    ]

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

    paid_at = models.DateTimeField(auto_now_add=True)
    initiated_at = models.DateTimeField(auto_now_add=True)

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
        Updates the account balance and fires notifications.
        """
        from django.utils import timezone
        from base.utils.signals import send_notification

        self.status = 'completed'
        self.transaction_ref = transaction_ref
        self.provider_ref = provider_ref
        self.paid_at = timezone.now()
        self.save()  # now safe — only checks is_cleared on creation, not here

        # the ONLY place amount_paid is updated
        balance = self.account.balance
        if self.amount > balance:
            OverDraft.objects.create(
                account=self.account,
                amount=self.amount - balance,
                transaction=self
            )
            self.account.amount_paid += balance
        else:
            self.account.amount_paid += self.amount
        self.account.save()

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
