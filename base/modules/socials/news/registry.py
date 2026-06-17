from typing import Dict, List
from .backends import AbstractNewsBackend


class NewsRegistry:
    """
    Maps news source names to their registered backend tools.

    Register in AppConfig.ready():
        news_registry.register(WordPressNewsBackend())
        news_registry.register(RSSNewsBackend())
    """

    # Shared storage that stays the same across the whole application
    _backends: Dict[str, AbstractNewsBackend] = {}

    @classmethod
    def register(cls, backend: AbstractNewsBackend):
        """
        Add a new news source backend tool to the global registry.
        """
        # Create a clean, lowercase name with dashes for the key lookup
        name = backend.source_name.lower().replace(" ", "-")
        if name:
            cls._backends[name] = backend

    @classmethod
    def get(cls, name: str) -> AbstractNewsBackend:
        """
        Grab a specific news backend tool using its unique short name.
        """
        return cls._backends.get(name.lower())

    @classmethod
    def all(cls) -> Dict[str, AbstractNewsBackend]:
        """
        Get the full dictionary of all active news backend tools.
        """
        return dict(cls._backends)


# The standard global instance for the system to import and use
news_registry = NewsRegistry()
