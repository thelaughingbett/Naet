"""
Events Registry System

This module handles the global mapping of unique event source names to their 
respective event backend integration handlers. 

All backend handlers must subclass `AbstractEventsBackend` and register with this 
central registry during the application startup hook phase to be discovered by 
background workers and webhook routes.
"""

from typing import Dict
from events.backends.base import AbstractEventsBackend


class EventsRegistry:
    """
    Maps event source names to their registered backend tools.

    Register in AppConfig.ready():
        events_registry.register(GoogleCalendarEventsBackend())
        events_registry.register(ICalEventsBackend())
    """

    # Shared storage that stays identical across the application footprint
    _backends: Dict[str, AbstractEventsBackend] = {}

    @classmethod
    def register(cls, backend: AbstractEventsBackend):
        """
        Add a new event source backend tool to the global registry.
        """
        # Create a clean, lowercase name with dashes for the key lookup
        name = backend.source_name.lower().replace(" ", "-")
        if name:
            cls._backends[name] = backend

    @classmethod
    def get(cls, name: str) -> AbstractEventsBackend:
        """
        Grab a specific event backend tool using its unique short name.
        """
        return cls._backends.get(name.lower())

    @classmethod
    def all(cls) -> Dict[str, AbstractEventsBackend]:
        """
        Get the full dictionary of all active event backend tools.
        """
        return dict(cls._backends)


# The standard global instance for the system to import and use
events_registry = EventsRegistry()
