"""
Custom PHP Portal Integration Backend

This module connects to a custom corporate PHP website. It handles pulling
JSON data feeds and verifying signed webhook push notifications.
"""

import datetime
import hmac
import hashlib
import logging
from events.backends.base import AbstractEventsBackend, EventFetchResult, Event, EventWebhookResult

logger = logging.getLogger(__name__)


class CustomPHPNewsBackend(AbstractEventsBackend):
    """
    Core backend tool to sync events from a custom PHP website portal.
    """
    # This name becomes the unique registry key: "custom-php-portal"
    source_name: str = "Custom PHP Portal"

    def fetch(self, limit: int = 50, upcoming_only: bool = True) -> EventFetchResult:
        """
        Pull event items from the PHP site's custom JSON endpoint feed.
        """
        try:
            # Imagine a web client fetching data from: https://php-site.com
            mock_php_payload = [
                {
                    "event_id": "php-event-404",
                    "event_title": "PHP Developer Meetup",
                    "event_desc": "Gathering to talk about clean code and object mapping.",
                    "event_category": "Social",
                    "event_date": "2026-07-15",
                    "venue": "Room B, Innovation Hub",
                    "is_virtual": 1,  # PHP often sends 1 or 0 for true and false flags
                    "join_link": "https://google.com",
                    "url": "https://php-site.com"
                }
            ]

            clean_events = []
            for item in mock_php_payload[:limit]:
                # Turn the PHP string into a clean date object
                date_str = item.get("event_date", "")
                event_date = datetime.date.fromisoformat(
                    date_str) if date_str else datetime.date.today()

                # Skip past calendar items if upcoming_only is turned on
                if upcoming_only and event_date < datetime.date.today():
                    continue

                # Build our standardized core event data shape
                event = Event(
                    external_id=str(item.get("event_id")),
                    title=item.get("event_title", "Untitled PHP Event"),
                    description=item.get("event_desc", ""),
                    category=item.get("event_category", "Social"),
                    date=event_date,
                    source_name=self.source_name,
                    location=item.get("venue"),
                    # Turn 1 or 0 into True or False
                    is_online=bool(item.get("is_virtual")),
                    meeting_url=item.get("join_link"),
                    source_url=item.get("url"),
                    raw=item
                )
                clean_events.append(event)

            return EventFetchResult(success=True, events=clean_events)

        except Exception as e:
            logger.error(f"Failed fetching from {self.source_name}: {str(e)}")
            return EventFetchResult(success=False, message=str(e))

    def verify_webhook(self, request) -> EventWebhookResult:
        """
        Verify a signed push notification sent by the PHP site.

        The PHP server signs the body content using an HMAC SHA256 secret key.
        """
        try:
            # Grab the signature header sent by the PHP hash_hmac() function
            php_signature = request.headers.get("X-PHP-Signature", "")
            raw_body_bytes = request.body  # The raw unparsed text bytes from the request

            if not php_signature:
                return EventWebhookResult(valid=False, message="Missing signature header")

            # Calculate our own signature check using our shared secret string key
            shared_secret = b"my-shared-php-secret-phrase"
            expected_signature = hmac.new(
                shared_secret,
                raw_body_bytes,
                hashlib.sha256
            ).hexdigest()

            # Compare signatures safely to protect against timing security bugs
            if not hmac.compare_digest(php_signature, expected_signature):
                return EventWebhookResult(valid=False, message="Signature match failed")

            # Webhook is safe! Check if this is a save action or a delete action
            mock_payload = request.json_payload or {}
            action_type = "upsert"
            if mock_payload.get("status") == "deleted":
                action_type = "delete"

            return EventWebhookResult(valid=True, action=action_type, message="PHP webhook verified")

        except Exception as e:
            return EventWebhookResult(valid=False, message=str(e))
