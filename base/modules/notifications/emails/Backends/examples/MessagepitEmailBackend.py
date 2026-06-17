# base/modules/notifications/email/backends/messagepit.py
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings

from base.modules.notifications.emails.base import (
    AbstractEmailBackend,
    EmailPayload
)
from base.modules.notifications.base import NotificationResult

logger = logging.getLogger('notifications')

_DEFAULT_SMTP_HOST = getattr(settings, 'MESSAGEPIT_SMTP_HOST', 'localhost')
_DEFAULT_SMTP_PORT = getattr(settings, 'MESSAGEPIT_SMTP_PORT', 1025)
_DEFAULT_FROM = getattr(settings, 'DEFAULT_FROM_EMAIL',   'dev@localhost')


class MessagePitEmailBackend(AbstractEmailBackend):
    """
    Captures outgoing email in MessagePit's SMTP server (port 1025).
    View captured emails at http://localhost:8025 → Inbox tab.
    """
    provider_name = "messagepit_email"

    def __init__(self, smtp_host: str = None, smtp_port: int = None):
        self.smtp_host = smtp_host or _DEFAULT_SMTP_HOST
        self.smtp_port = smtp_port or _DEFAULT_SMTP_PORT

    def send(self, payload: EmailPayload) -> NotificationResult:
        from_address = payload.from_address or _DEFAULT_FROM
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = payload.subject
            msg['From'] = from_address
            msg['To'] = payload.to_address
            if payload.reply_to:
                msg['Reply-To'] = payload.reply_to

            msg.attach(MIMEText(payload.text_body, 'plain'))
            msg.attach(MIMEText(payload.html_body,  'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as smtp:
                smtp.sendmail(
                    from_address, [payload.to_address], msg.as_string())

            logger.debug(
                f"[messagepit_email] Captured → to={payload.to_address} "
                f"subject='{payload.subject}'  view at http://localhost:8025"
            )
            return NotificationResult(
                success=True,
                message_id=msg.get('Message-ID'),
                message=f"Captured by MessagePit (to={payload.to_address})",
            )

        except ConnectionRefusedError:
            msg = (
                f"Could not connect to MessagePit SMTP at "
                f"{self.smtp_host}:{self.smtp_port}. "
                "Is messagepit.exe running?"
            )
            logger.warning(f"[messagepit_email] {msg}")
            return NotificationResult(success=False, message=msg)

        except Exception as e:
            logger.exception(f"[messagepit_email] Unexpected error: {e}")
            return NotificationResult(success=False, message=str(e))

    def health_check(self) -> bool:
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=3):
                return True
        except Exception:
            return False
