"""
Events Backend Module & Registry System

This module implements an open, pluggable architecture for event calendars. 
Every event provider must inherit from `AbstractEventsBackend` and register 
its instance with the system's global backend registry.


Folder Structure Reference:
    events/
    ├── backends/            <-- Pure directory layout
    │   ├── contrib/              <-- Community Open-Source Contributions Go Here
    │   │     
    │   ├── __init__.py      # This file (handles initialization)
    │   └── base.py          # Contains AbstractEventsBackend and dataclasses
    ├── registry.py          # Central registry engine
    ├── tasks.py             # Background automation worker logic
    ├── urls.py              # Centralized webhook routing endpoints
    └── views.py             # Global webhook receiving controller

Where to Write Your Custom Backend:

    1. Local Integrator / Corporate Setup:
       Write your calendar feed module directly inside the core `events/backends/` 
       directory alongside `base.py`.
       
    2. Open-Source Contributor Setup:
       Write your vendor-specific feed module inside the `events/contrib/backends/` 
       directory to keep the core code footprint clean and maintainable.

Registration Patterns:

    Pattern A: Static Registration (Core / Integrator / Contributor Modules)
    ------------------------------------------------------------------------
    Import and register your backend instance explicitly inside the initialization 
    sequence of your application startup hook, or directly in this init package:

        from events.registry import events_registry
        from events.backends.google_calendar import GoogleCalendarEventsBackend
        from events.contrib.backends.ical import ICalEventsBackend

        events_registry.register(GoogleCalendarEventsBackend())
        events_registry.register(ICalEventsBackend())

    Pattern B: Dynamic Integration (Third-Party Isolated Django Apps)
    ------------------------------------------------------------------
    If your backend lives in a detached third-party module app, register it via 
    Django's Application Configuration startup hook:

        # outside_app/apps.py
        from django.apps import AppConfig

        class OutsideAppConfig(AppConfig):
            name = 'outside_app'

            def ready(self):
                from events.registry import events_registry
                from .backends import CustomCalendarBackend
                
                events_registry.register(CustomCalendarBackend())

Execution Flow Contract:
    - Custom backends must NEVER modify database records inside `fetch()` or `verify_webhook()`.
    - Always yield standard `EventFetchResult` or `EventWebhookResult` data structures.
    - Status calculation, RSVP cutoff tracking, and ledger safety are securely handled by core.
"""
from .base import *
