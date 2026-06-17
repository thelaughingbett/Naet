# base/modules/notifications/sms/backends/messagepit.py
import logging
import requests
from django.conf import settings

from base.modules.notifications.sms.base import AbstractSMSBackend, SMSPayload
from base.modules.notifications.base import NotificationResult

logger = logging.getLogger('notifications')

_DEFAULT_SMS_URL = getattr(
    settings,
    'MESSAGEPIT_SMS_URL',
    'http://localhost:8200'
)


class MessagePitSMSBackend(AbstractSMSBackend):
    """
    Captures outgoing SMS in MessagePit's Twilio-compatible ingest (port 8200).
    View captured messages at http://localhost:8025 → SMS tab.
    """
    provider_name = "messagepit_sms"

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or _DEFAULT_SMS_URL).rstrip('/')
        self._endpoint = f"{self.base_url}/2010-04-01/Accounts/test/Messages.json"

    def send(self, payload: SMSPayload) -> NotificationResult:
        from_number = payload.sender_id or getattr(
            settings, 'SMS_SENDER_ID', '+15550000000')
        try:
            response = requests.post(
                self._endpoint,
                data={'From': from_number,
                      'To': payload.to_number, 'Body': payload.body},
                auth=('test', 'test'),
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(
                f"[messagepit_sms] Captured → to={payload.to_number} "
                f"sid={data.get('sid')}  view at http://localhost:8025"
            )
            return NotificationResult(
                success=True,
                message_id=data.get('sid'),
                message=f"Captured by MessagePit (to={payload.to_number})",
                raw_response=data,
            )

        except requests.exceptions.ConnectionError:
            msg = (
                f"Could not connect to MessagePit at {self.base_url}. "
                "Is messagepit.exe running?"
            )
            logger.warning(f"[messagepit_sms] {msg}")
            return NotificationResult(success=False, message=msg)

        except Exception as e:
            logger.exception(f"[messagepit_sms] Unexpected error: {e}")
            return NotificationResult(success=False, message=str(e))

    def health_check(self) -> bool:
        try:
            r = requests.get(self.base_url, timeout=3)
            return r.status_code < 500
        except Exception:
            return False
