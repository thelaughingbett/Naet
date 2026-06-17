# base/modules/notifications/backends/sendgrid.py

import sendgrid
from sendgrid.helpers.mail import Mail, To, From
from django.conf import settings
from base.modules.notifications.base import NotificationResult
from base.modules.notifications.emails.base import (
    AbstractEmailBackend, EmailPayload
)


class SendGridEmailBackend(AbstractEmailBackend):
    """
    Email via SendGrid.

    Settings required:
        SENDGRID_API_KEY    = 'SG.xxxx'
        DEFAULT_FROM_EMAIL  = 'noreply@university.ac.ke'
    """

    provider_name = "sendgrid"

    def __init__(self):
        self._client = sendgrid.SendGridAPIClient(
            api_key=settings.SENDGRID_API_KEY)

    def send(self, payload: EmailPayload) -> NotificationResult:
        try:
            message = Mail(
                from_email=payload.from_address or settings.DEFAULT_FROM_EMAIL,
                to_emails=payload.to_address,
                subject=payload.subject,
                html_content=payload.html_body,
                plain_text_content=payload.text_body,
            )
            response = self._client.send(message)

            if response.status_code in (200, 202):
                return NotificationResult(
                    success=True,
                    message_id=response.headers.get('X-Message-Id'),
                    message=f"Sent to {payload.to_address}",
                    raw_response={'status_code': response.status_code},
                )

            return NotificationResult(
                success=False,
                message=f"SendGrid returned {response.status_code}",
                raw_response={'status_code': response.status_code,
                              'body': response.body},
            )

        except Exception as e:
            return NotificationResult(success=False, message=str(e))
