# 🎉 Events Module

> How university events get from wherever they live (a CMS, a Google Calendar,
> a spreadsheet, a webhook, someone's head) into the student portal —
> and how you can add a new events source without touching a single line
> of core code.

---

## 🗺️ Overview

Events in Naet follow the same pluggable architecture as payments and news.
The system doesn't care where events come from. It only cares that whatever
comes in looks like an `Event` dataclass.

```
External source (CMS, Google Calendar, RSS, manual admin entry)
      ↓
AbstractEventsBackend.fetch()       ← your backend normalises it
      ↓
EventItem stored in DB              ← or rendered directly if no DB
      ↓
EventsView queries EventItem        ← student sees it
```

There are two modes depending on what the institution has set up:

| Mode                      | When                                            | How                                                                                   |
| ------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Model-backed** (Mode A) | Backends registered + Celery running            | Sync runs every 30 min, stores into `EventItem` — fast, filterable, searchable        |
| **Live** (Mode B)         | Backends registered, no Celery / no DB rows yet | View calls `backend.fetch()` on each request — slower but zero DB setup               |
| **Manual**                | No backends, admin adds events directly         | `EventItem` rows created in Django admin — same as Mode A from the view's perspective |

---

## 🏗️ Architecture

```
events/
├── backends/
│   ├── __init__.py       # exports AbstractEventsBackend + dataclasses
│   ├── base.py           # the contract
│   └── contrib/          # community-contributed backends
│       └── README.md
├── registry.py           # EventsRegistry singleton
├── sync.py               # upsert_event() + unpublish_event() — shared helpers
├── tasks.py              # Celery beat task: sync_event_feeds()
├── urls.py               # webhook routing
└── views.py              # EventsWebhookView
```

---

## 📐 The Contract

```python
class AbstractEventsBackend(ABC):

    source_name: str = ""   # shown in admin/logs, used as webhook route key

    @abstractmethod
    def fetch(self, limit: int = 50, upcoming_only: bool = True) -> EventFetchResult:
        """
        Pull events from the source. Normalise them into Event dataclasses.
        Called by the Celery task on a schedule.
        DO NOT save anything here.
        Catch all exceptions — return EventFetchResult(success=False) instead of raising.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request) -> EventWebhookResult:
        """
        Parse + verify an inbound push from the CMS.
        Set action='delete' if the event was cancelled — Naet will unpublish it.
        DO NOT save anything here.
        """
        raise NotImplementedError
```

### 📦 The dataclasses

| Dataclass            | Purpose                                                                |
| -------------------- | ---------------------------------------------------------------------- |
| `Event`              | The normalised shape of one event — title, date, times, location, RSVP |
| `EventFetchResult`   | Wraps a list of `Event` objects + success/failure info                 |
| `EventWebhookResult` | Result of verifying a push — includes `action: "upsert" \| "delete"`   |

### 🔑 Key fields on `Event`

```python
@dataclass
class Event:
    external_id:   str              # unique ID in the source system
    title:         str
    description:   str
    category:      str
    date:          datetime.date
    source_name:   str

    start_time:    Optional[datetime.time] = None
    end_time:      Optional[datetime.time] = None
    location:      Optional[str] = None
    is_online:     bool = False
    meeting_url:   Optional[str] = None   # Zoom / Teams / Meet

    badge:         Optional[str] = None
    thumbnail:     Optional[str] = None
    source_url:    Optional[str] = None   # full details page
    rsvp_url:      Optional[str] = None
    rsvp_deadline: Optional[datetime.date] = None

    # computed — no need to set these
    @property
    def status(self) -> str: ...       # 'upcoming' | 'ongoing' | 'past'

    @property
    def is_rsvp_open(self) -> bool: ...
```

> 💡 Both `Event` (dataclass) and `EventItem` (model) expose `.status` and
> `.is_rsvp_open` as properties with identical logic — so the template
> doesn't care which mode it's in.

---

## 🛠️ Adding a New Backend

### Step 1 — Decide where your file lives

Community contribution:

```
events/backends/contrib/google_calendar.py
```

Institution-specific:

```
events/backends/google_calendar.py
```

### Step 2 — Implement the contract

```python
from events.backends.base import (
    AbstractEventsBackend,
    Event,
    EventFetchResult,
    EventWebhookResult,
)
import datetime
import requests


class GoogleCalendarBackend(AbstractEventsBackend):

    source_name = "google-calendar"

    def fetch(self, limit=50, upcoming_only=True) -> EventFetchResult:
        try:
            response = requests.get(
                "https://www.googleapis.com/calendar/v3/calendars/.../events",
                params={
                    'key':        settings.GOOGLE_CALENDAR_API_KEY,
                    'maxResults': limit,
                    'timeMin':    datetime.datetime.utcnow().isoformat() + 'Z' if upcoming_only else None,
                    'singleEvents': True,
                    'orderBy':    'startTime',
                }
            )
            response.raise_for_status()
            data = response.json()

        except Exception as e:
            return EventFetchResult(success=False, message=str(e))

        events = []
        for item in data.get('items', []):
            start = item.get('start', {})
            end   = item.get('end', {})

            events.append(Event(
                external_id=  item['id'],
                title=        item.get('summary', 'Untitled'),
                description=  item.get('description', ''),
                category=     item.get('extendedProperties', {}).get('private', {}).get('category', 'General'),
                date=         datetime.date.fromisoformat(start.get('date') or start.get('dateTime', '')[:10]),
                source_name=  self.source_name,
                start_time=   _parse_time(start.get('dateTime')),
                end_time=     _parse_time(end.get('dateTime')),
                location=     item.get('location'),
                source_url=   item.get('htmlLink'),
            ))

        return EventFetchResult(success=True, events=events)

    def verify_webhook(self, request) -> EventWebhookResult:
        # Google Calendar uses push notifications — implement verification here
        # For now, return valid=False to disable webhook support
        return EventWebhookResult(valid=False, message="Webhook not supported for Google Calendar")


def _parse_time(dt_string):
    if not dt_string:
        return None
    try:
        return datetime.datetime.fromisoformat(dt_string).time()
    except ValueError:
        return None
```

### Step 3 — Register it

```python
# base/apps.py
class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        from events.registry import events_registry
        from events.backends.google_calendar import GoogleCalendarBackend

        events_registry.register(GoogleCalendarBackend())
```

### Step 4 — Add to Celery schedule (optional)

If you want the sync to run automatically:

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'sync-event-feeds': {
        'task':     'events.tasks.sync_event_feeds',
        'schedule': 60 * 30,   # every 30 minutes
    },
}
```

---

## 🔄 The Sync Flow (Mode A)

```
Celery beat fires every 30 min
      ↓
sync_event_feeds() iterates events_registry.all()
      ↓
backend.fetch() called per registered backend
      ↓
Each Event → upsert_event(event) → EventItem.update_or_create(external_id=...)
      ↓
EventsView queries EventItem — always fast, always DB-backed
```

### Cancellations

If a CMS cancels an event and pushes a webhook with `action='delete'`:

```python
# sync.py
def unpublish_event(external_id: str):
    EventItem.objects.filter(external_id=external_id).update(is_published=False)
```

We **unpublish** rather than delete — so cancelled events stay in admin history.

---

## 🔗 Webhook Route

Each backend's webhook endpoint is auto-routed:

```
POST /events/webhook/<source_name>/
```

So `GoogleCalendarBackend` with `source_name = "google-calendar"` gets:

```
POST /events/webhook/google-calendar/
```

To get the full URL for registering with an external CMS:

```python
from django.urls import reverse
url = reverse('events-webhook', kwargs={'source_name': backend.source_name})
```

---

## 🚦 The Golden Rules

**1. Never save anything inside `fetch()` or `verify_webhook()`**
`upsert_event()` and `unpublish_event()` in `sync.py` own all DB writes.
Your backend owns the external API conversation only.

**2. Always return a result dataclass — never raise**
If your API is down, return `EventFetchResult(success=False, message=str(e))`.
The sync task logs it and moves on to the next backend.

**3. `external_id` must be stable and unique within your source**
This is what deduplication is built on. If your source changes IDs,
you'll get duplicate events in the DB.

**4. `action='delete'` unpublishes — it doesn't delete**
The template won't show it, but the admin record stays. This is intentional.

---

## 🏫 Manual Events (No Backend)

If an institution doesn't have a CMS, events can be created directly
in the Django admin:

```
Admin → Events → EventItems → Add
```

Use a namespaced `external_id` to avoid future collisions with a backend:

```
manual:graduation-ceremony-2026
manual:sports-day-june-2026
```

Or switch to `unique_together = ('source_name', 'external_id')` on the model
and set `source_name = 'manual'` for admin-created items.

---

## 🧪 Testing your backend

```python
class GoogleCalendarBackendTest(TestCase):

    @patch('events.backends.google_calendar.requests.get')
    def test_fetch_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            'items': [{
                'id': 'evt-001',
                'summary': 'Tech Symposium',
                'description': 'Annual tech expo',
                'start': {'dateTime': '2026-06-15T09:00:00'},
                'end':   {'dateTime': '2026-06-15T17:00:00'},
                'location': 'Main Hall',
                'htmlLink': 'https://calendar.google.com/...',
            }]
        }

        backend = GoogleCalendarBackend()
        result  = backend.fetch(limit=10)

        self.assertTrue(result.success)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].title, 'Tech Symposium')
        self.assertEqual(result.events[0].external_id, 'evt-001')

    @patch('events.backends.google_calendar.requests.get')
    def test_fetch_api_failure(self, mock_get):
        mock_get.side_effect = Exception("Connection timeout")

        backend = GoogleCalendarBackend()
        result  = backend.fetch()

        self.assertFalse(result.success)
        self.assertIn('timeout', result.message)
```

---

## 🔗 Where to Go Next

| Topic                         | Document                         |
| ----------------------------- | -------------------------------- |
| 📰 News module (same pattern) | [News Module](news.md)           |
| 💳 Payments module            | [Payments Module](payments.md)   |
| 🗃️ EventItem model fields     | [Models Reference](../models.md) |
| 📋 Registry pattern           | `events/registry.py`             |
