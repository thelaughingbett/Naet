# payments/service.py

from django.db import transaction as db_transaction
from django.utils import timezone
from .registry import registry
from .backends import PaymentInitiationResult


class PaymentService:
    """
    Core payment orchestration.
    Knows nothing about M-Pesa or banks — only about Payment records.
    """

    @staticmethod
    def initiate(payment, **kwargs) -> PaymentInitiationResult:
        """
        Initiates a payment through the registered backend for payment.method.
        Updates payment.provider_ref if the backend returns one.
        """
        backend = registry.get(payment.method)
        result = backend.initiate(payment, **kwargs)

        if result.success:
            payment.provider_ref = result.provider_ref
            payment.status = result.status
            payment.save(update_fields=['provider_ref', 'status'])

        else:
            payment.status = result.status
            payment.save(update_fields=['status'])

        return result

    @staticmethod
    def confirm(payment, transaction_ref: str, provider_ref: str = None):
        """
        Confirms a payment — called by the webhook handler.
        Updates account balance and fires notifications.
        This is the same regardless of provider.
        """
        from base.utils.signals import send_notification
        from base.models import OverDraft

        with db_transaction.atomic():
            payment.status = 'completed'
            payment.transaction_ref = transaction_ref
            payment.provider_ref = provider_ref or payment.provider_ref
            payment.paid_at = timezone.now()
            payment.save()

            account = payment.account
            balance = account.balance

            # if payment.amount > balance:
            #     OverDraft.objects.create(
            #         account=account,
            #         amount=payment.amount - balance,
            #         transaction=payment
            #     )
            #     account.amount_paid += balance
            # else:
            #     account.amount_paid += payment.amount

            account.save()

        # fire notification outside the transaction
        db_transaction.on_commit(lambda: send_notification.send(
            sender=payment.__class__,
            user=payment.account.student.user,
            template_key='payment_confirmed',
            channels=['sms', 'email'],
            context={
                'student_name': payment.account.student.user.full_name,
                'amount':       payment.amount,
                'method':       payment.get_method_display(),
                'ref':          payment.transaction_ref,
                'balance':      payment.account.balance,
                'is_cleared':   payment.account.is_cleared,
            }
        ))

    @staticmethod
    def fail(payment, reason: str = ""):
        """Marks a payment as failed."""
        from base.utils.signals import send_notification

        payment.status = 'failed'
        payment.save(update_fields=['status'])

        db_transaction.on_commit(lambda: send_notification.send(
            sender=payment.__class__,
            user=payment.account.student.user,
            template_key='payment_failed',
            channels=['sms'],
            context={
                'student_name': payment.account.student.user.full_name,
                'amount':       payment.amount,
                'reason':       reason,
            }
        ))
