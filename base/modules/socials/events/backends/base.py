# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import datetime


@dataclass
class Event:
    """
    The normalised shape of an event from any source.

    Time fields are optional — some sources only give a date.
    location and meeting_url are mutually exclusive but both optional
    (an event can be physical-only, online-only, or hybrid).
    """
    external_id:   str
    title:         str
    description:   str
    category:      str                          # "Academic", "Sports", "Social"
    date:          datetime.date
    source_name:   str

    start_time:    Optional[datetime.time] = None
    end_time:      Optional[datetime.time] = None

    location:      Optional[str] = None         # physical venue
    is_online:     bool = False
    meeting_url:   Optional[str] = None         # Zoom / Teams / Meet link

    badge:         Optional[str] = None         # "⭐ Featured", "🔴 Urgent"
    thumbnail:     Optional[str] = None

    source_url:    Optional[str] = None         # full details page
    rsvp_url:      Optional[str] = None         # external registration form
    rsvp_deadline: Optional[datetime.date] = None

    raw:           Optional[dict] = None

    @property
    def status(self) -> str:
        today = datetime.date.today()
        if self.date > today:
            return 'upcoming'
        if self.date == today:
            return 'ongoing'
        return 'past'

    @property
    def is_rsvp_open(self) -> bool:
        if not self.rsvp_url:
            return False
        if self.rsvp_deadline:
            return datetime.date.today() <= self.rsvp_deadline
        return self.status == 'upcoming'


@dataclass
class EventFetchResult:
    """
    Returned by every events backend after fetching events.
    """
    success: bool
    events:  list[Event] = field(default_factory=list)
    message: str = ""
    raw:     Optional[dict] = None


@dataclass
class EventWebhookResult:
    """
    Returned after verifying an inbound event push.
    """
    valid:   bool
    event:   Optional[Event] = None
    action:  str = "upsert"             # "upsert" | "delete" — CMS may cancel events
    message: str = ""
    raw:     Optional[dict] = None


class AbstractEventsBackend(ABC):
    """
    Contract every events source must implement.

    Integrators subclass this and implement fetch() and verify_webhook().
    Naet handles storage, status computation (upcoming/ongoing/past),
    and RSVP deadline checks.

    Example implementations:
        - GoogleCalendarEventsBackend  → polls Google Calendar API
        - WordPressEventsBackend       → polls The Events Calendar plugin API
        - ICalEventsBackend            → parses a .ics feed
        - WebhookEventsBackend         → accepts push from a custom system

    Usage in settings.py:
        EVENTS_BACKEND = 'myapp.integrations.events.GoogleCalendarEventsBackend'
    """

    source_name: str = ""

    @abstractmethod
    def fetch(self, limit: int = 50, upcoming_only: bool = True) -> EventFetchResult:
        """
        Pull events from the source.

        Called by Celery beat task on a schedule.
        Return EventFetchResult with normalised Event objects.

        upcoming_only=True → only fetch future events (skip past ones).
        Naet will update_or_create on external_id.

        Do NOT save anything here.
        Catch all exceptions internally and return EventFetchResult(success=False).
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request) -> EventWebhookResult:
        """
        Parse and verify an inbound webhook push.

        Check the signature, parse the payload.
        Set action='delete' if the CMS is cancelling an event —
        Naet will unpublish it rather than delete it.

        Return valid=False if verification fails.
        Do NOT save anything here.
        """
        raise NotImplementedError

    def get_webhook_url_name(self) -> str:
        return f'webhook-events-{self.source_name.lower().replace(" ", "-")}'
