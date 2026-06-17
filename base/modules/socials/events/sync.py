"""
Shared mapping from the normalised `Event` dataclass to `EventItem` fields.
Used by both the scheduled sync task and the webhook handler.
"""

from base.models import EventItem
from events.backends.base import Event


def event_to_defaults(event: Event) -> dict:
    return {
        'title':         event.title,
        'description':   event.description,
        'category':      event.category,
        'date':          event.date,
        'start_time':    event.start_time,
        'end_time':      event.end_time,
        'location':      event.location,
        'is_online':     event.is_online,
        'meeting_url':   event.meeting_url,
        'badge':         event.badge,
        'thumbnail':     event.thumbnail,
        'source_url':    event.source_url,
        'source_name':   event.source_name,
        'rsvp_url':      event.rsvp_url,
        'rsvp_deadline': event.rsvp_deadline,
        'is_published':  True,
    }


def upsert_event(event: Event) -> EventItem:
    obj, _ = EventItem.objects.update_or_create(
        external_id=event.external_id,
        defaults=event_to_defaults(event),
    )
    return obj


def unpublish_event(external_id: str) -> None:
    """
    Called when a backend reports action='delete' — per the
    AbstractEventsBackend contract we unpublish rather than delete,
    so cancelled events still show in history/admin.
    """
    EventItem.objects.filter(
        external_id=external_id).update(is_published=False)
