# base/modules/notifications/service.py

import logging
from django.conf import settings

from base.modules.notifications.registry import notification_registry
from base.modules.notifications.emails.base import EmailPayload
from base.modules.notifications.sms.base import SMSPayload
from base.modules.notifications.templates import render_email, render_sms

logger = logging.getLogger('notifications')


class NotificationService:
    """
    The only entry point for sending notifications.

    Handles:
    - Template rendering
    - Backend routing (email / sms / both)
    - Logging successes and failures
    - Graceful degradation if a backend isn't configured

    Usage:
        NotificationService.send(
            user=payment.account.student.user,
            template_key='payment_confirmed',
            channels=['email', 'sms'],
            context={
                'student_name': user.full_name,
                'amount':       payment.amount,
                'ref':          payment.transaction_ref,
                'balance':      account.balance,
            }
        )
    """

    @classmethod
    def send(cls, user, template_key: str, channels: list[str], context: dict):
        """
        Send a notification to a user across one or more channels.
        Never raises — logs failures and moves on.
        """
        for channel in channels:
            try:
                if channel == 'email':
                    cls._send_email(user, template_key, context)
                elif channel == 'sms':
                    cls._send_sms(user, template_key, context)
                else:
                    logger.warning(
                        f"[notifications] Unknown channel '{channel}' — skipped")

            except Exception as e:
                # don't let one channel failure kill the others
                logger.error(
                    f"[notifications] Unexpected error on channel '{channel}' "
                    f"for template '{template_key}': {e}"
                )

    @classmethod
    def _send_email(cls, user, template_key: str, context: dict):
        if not notification_registry.has_email():
            logger.warning(
                f"[notifications] No email backend registered — "
                f"'{template_key}' email to {user.email} skipped"
            )
            return

        try:
            subject, html_body, text_body = render_email(template_key, context)
        except ValueError as e:
            logger.error(f"[notifications] Email template error: {e}")
            return

        payload = EmailPayload(
            to_address=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_address=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        )

        backend = notification_registry.get_email()
        result = backend.send(payload)

        if result.success:
            logger.info(
                f"[notifications] Email sent via {backend.provider_name} — "
                f"template='{template_key}' to={user.email} id={result.message_id}"
            )
        else:
            logger.error(
                f"[notifications] Email failed via {backend.provider_name} — "
                f"template='{template_key}' to={user.email} error={result.message}"
            )

    @classmethod
    def _send_sms(cls, user, template_key: str, context: dict):
        phone = getattr(user, 'phone_number',
                        None) or context.get('phone_number')

        if not phone:
            logger.warning(
                f"[notifications] No phone number for user {user.email} — "
                f"'{template_key}' SMS skipped"
            )
            return

        if not notification_registry.has_sms():
            logger.warning(
                f"[notifications] No SMS backend registered — "
                f"'{template_key}' SMS to {phone} skipped"
            )
            return

        try:
            body = render_sms(template_key, context)
        except ValueError as e:
            logger.error(f"[notifications] SMS template error: {e}")
            return

        payload = SMSPayload(
            to_number=phone,
            body=body,
            sender_id=getattr(settings, 'SMS_SENDER_ID', None),
        )

        backend = notification_registry.get_sms()
        result = backend.send(payload)

        if result.success:
            logger.info(
                f"[notifications] SMS sent via {backend.provider_name} — "
                f"template='{template_key}' to={phone} id={result.message_id}"
            )
        else:
            logger.error(
                f"[notifications] SMS failed via {backend.provider_name} — "
                f"template='{template_key}' to={phone} error={result.message}"
            )
