"""
Google Calendar Event Integration Backend

This module connects directly to the core Google Calendar API to pull 
and verify physical site scheduling feeds.
"""

import datetime
import logging
from events.backends.base import (
    AbstractEventsBackend,
    EventFetchResult,
    Event,
    EventWebhookResult
)

logger = logging.getLogger(__name__)


class GoogleCalendarEventsBackend(AbstractEventsBackend):
    """
    Core backend tool to pull calendar event feeds from the Google Calendar API.
    """
    # This name becomes the unique registry key: "google-calendar"
    source_name: str = "Google Calendar"

    def fetch(self, limit: int = 50, upcoming_only: bool = True) -> EventFetchResult:
        """
        Pull event entries from the Google Calendar resource endpoint.
        """
        try:
            # Imagine an API request getting JSON data items here
            mock_api_payload = [
                {
                    "id": "gcal-2026-001",
                    "summary": "Annual Sports Day Championship",
                    "description": "Track and field competitions for all departments.",
                    "location": "Main University Stadium",
                    "start": {"date": "2026-06-20", "dateTime": "10:00:00"},
                    "end": {"date": "2026-06-20", "dateTime": "16:00:00"},
                    "htmlLink": "https://google.com"
                }
            ]

            clean_events = []
            for item in mock_api_payload[:limit]:
                # Extract date and time strings safely
                event_date = datetime.date.fromisoformat(item["start"]["date"])

                # Filter out past events if the task asks for upcoming items only
                if upcoming_only and event_date < datetime.date.today():
                    continue

                event = Event(
                    external_id=str(item.get("id")),
                    title=item.get("summary", "Untitled Event"),
                    description=item.get("description", ""),
                    category="Sports",
                    date=event_date,
                    source_name=self.source_name,
                    start_time=datetime.time.fromisoformat(
                        item["start"]["dateTime"]),
                    end_time=datetime.time.fromisoformat(
                        item["end"]["dateTime"]),
                    location=item.get("location"),
                    is_online=False,
                    source_url=item.get("htmlLink"),
                    raw=item
                )
                clean_events.append(event)

            return EventFetchResult(success=True, events=clean_events)

        except Exception as e:
            logger.error(f"Failed fetching from {self.source_name}: {str(e)}")
            return EventFetchResult(success=False, message=str(e))

    def verify_webhook(self, request) -> EventWebhookResult:
        """
        Check push notifications from Google Calendar channel synchronizations.
        """
        try:
            # Check resource state channel token headers
            channel_token = request.headers.get("X-Goog-Channel-Token", "")
            if channel_token != "expected-secure-token":
                return EventWebhookResult(valid=False, message="Invalid token verification")

            return EventWebhookResult(valid=True, action="upsert")

        except Exception as e:
            return EventWebhookResult(valid=False, message=str(e))
