# base/modules/notifications/backends/africastalking.py

import africastalking
from django.conf import settings
from base.modules.notifications.base import NotificationResult

from base.modules.notifications.sms.base import (
    AbstractSMSBackend, SMSPayload
)


class AfricasTalkingBackend(AbstractSMSBackend):
    """
    SMS via Africa's Talking — the standard for Kenya.

    Settings required:
        AFRICASTALKING_USERNAME = 'your-username'
        AFRICASTALKING_API_KEY  = 'your-api-key'
        SMS_SENDER_ID           = 'NAET'   # optional shortcode
    """

    provider_name = "africastalking"

    def __init__(self):
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY,
        )
        self._sms = africastalking.SMS

    def send(self, payload: SMSPayload) -> NotificationResult:
        try:
            response = self._sms.send(
                message=payload.body,
                recipients=[payload.to_number],
                sender_id=payload.sender_id,
            )
            recipients = response.get(
                'SMSMessageData', {}).get('Recipients', [])
            first = recipients[0] if recipients else {}
            status = first.get('status', '')

            if status == 'Success':
                return NotificationResult(
                    success=True,
                    message_id=first.get('messageId'),
                    message=f"Delivered to {payload.to_number}",
                    raw_response=response,
                )

            return NotificationResult(
                success=False,
                message=first.get('status', 'Unknown error'),
                raw_response=response,
            )

        except Exception as e:
            return NotificationResult(success=False, message=str(e))
