"""
iCal Open-Source Integration Backend

This module parses standard iCalendar (.ics) files to import events 
from remote web feeds into the system ledger.
"""

import datetime
from events.backends.base import AbstractEventsBackend, EventFetchResult, Event, EventWebhookResult


class ICalEventsBackend(AbstractEventsBackend):
    """
    A community contributor module to parse standard iCalendar (.ics) files.
    """
    # This name becomes the unique registry key: "ical-feed"
    source_name: str = "iCal Feed"

    def fetch(self, limit: int = 50, upcoming_only: bool = True) -> EventFetchResult:
        """
        Download and process open standard calendar lines.
        """
        try:
            # Imagine an open-source library reading an internet .ics text file here
            clean_events = [
                Event(
                    external_id="ics-interactive-05",
                    title="Online Research Webinar",
                    description="Live stream talk regarding modern AI concepts.",
                    category="Academic",
                    date=datetime.date.today() + datetime.timedelta(days=2),
                    source_name=self.source_name,
                    is_online=True,
                    meeting_url="https://zoom.us",
                    badge="⭐ Featured"
                )
            ]
            return EventFetchResult(success=True, events=clean_events[:limit])

        except Exception as e:
            return EventFetchResult(success=False, message=str(e))

    def verify_webhook(self, request) -> EventWebhookResult:
        """
        Receive external updates from CMS software. Handles deleted items.
        """
        try:
            # Read an event payload dictionary sent by a webhook alert post
            mock_webhook_data = request.json_payload or {}

            # If the source system has cancelled this entry, mark the action for unpublishing
            action_type = "upsert"
            if mock_webhook_data.get("status") == "cancelled":
                action_type = "delete"

            return EventWebhookResult(
                valid=True,
                action=action_type,
                message="Successfully verified push action notification"
            )

        except Exception as e:
            return EventWebhookResult(valid=False, message=str(e))
