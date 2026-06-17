import logging
import requests
from django.conf import settings

logger = logging.getLogger('notifications')

# In dev, set WEBHOOK_BASE_URL = 'http://localhost:8300'
# In prod, set it to your real endpoint
WEBHOOK_BASE_URL = getattr(
    settings, 'WEBHOOK_BASE_URL', 'http://localhost:8300'
)


def fire_webhook(event: str, payload: dict):
    """
    Fire an outbound webhook. In dev this hits MessagePit's capture
    server on port 8300 and you can inspect it at http://localhost:8025
    under the Webhooks tab.

    Usage:
        fire_webhook('payment.confirmed', {
            'student_id': user.id,
            'amount': 5000,
            'ref': 'TXN-001',
        })
    """
    url = f"{WEBHOOK_BASE_URL}/webhooks/{event.replace('.', '/')}"

    try:
        response = requests.post(url, json={
            'event':   event,
            'payload': payload,
        }, timeout=5)

        logger.info(
            f"[webhook] fired event='{event}' → {url} "
            f"status={response.status_code}"
        )

    except requests.exceptions.ConnectionError:
        logger.warning(
            f"[webhook] Could not reach {url} — "
            "is messagepit.exe running?"
        )
    except Exception as e:
        logger.exception(f"[webhook] Unexpected error firing '{event}': {e}")
