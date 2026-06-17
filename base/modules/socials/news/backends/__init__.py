"""
News Backend Module & Registry System

This module implements an open, pluggable architecture for news source feeds. 
Every content provider must inherit from `AbstractNewsBackend` and register 
its instance with the system's global backend registry.


Folder Structure Reference:
    news/
    ├── backends/            <-- Pure directory layout
    │   ├── contrib/             
    │   │   └── backends/    <-- Community Open-Source Contributions Go Here
    │   ├── __init__.py      # This file (handles initialization)
    │   └── base.py          # Contains AbstractNewsBackend and dataclasses
    ├── registry.py          # Central registry engine
    ├── tasks.py             # Celery beat worker automation logic
    ├── urls.py              # Centralized webhook routing endpoints
    └── views.py             # Global webhook receiving controller

Where to Write Your Custom Backend:

    1. Local Integrator / Corporate Setup:
       Write your source feed module directly inside the core `news/backends/` 
       directory alongside `base.py`.
       
    2. Open-Source Contributor Setup:
       Write your vendor-specific feed module inside the `news/contrib/backends/` 
       directory to keep the core code footprint clean and maintainable.

Registration Patterns:

    Pattern A: Static Registration (Core / Integrator / Contributor Modules)
    ------------------------------------------------------------------------
    Import and register your backend instance explicitly inside the initialization 
    sequence of your application startup hook, or directly in this init package:

        from news.registry import news_registry
        from news.backends.wordpress import WordPressNewsBackend
        from news.contrib.backends.rss import RSSNewsBackend

        news_registry.register(WordPressNewsBackend())
        news_registry.register(RSSNewsBackend())

    Pattern B: Dynamic Integration (Third-Party Isolated Django Apps)
    ------------------------------------------------------------------
    If your backend lives in a detached third-party module app, register it via 
    Django's Application Configuration startup hook:

        # outside_app/apps.py
        from django.apps import AppConfig

        class OutsideAppConfig(AppConfig):
            name = 'outside_app'

            def ready(self):
                from news.registry import news_registry
                from .backends import CustomCMSBackend
                
                news_registry.register(CustomCMSBackend())

Execution Flow Contract:
    - Custom backends must NEVER modify database records inside `fetch()` or `verify_webhook()`.
    - Always yield standard `NewsFetchResult` or `WebhookVerificationResult` data structures.
    - Article deduplication, storage updates, and sync logging are securely handled by core.
"""

from .base import (
    NewsArticle,
    NewsFetchResult,
    WebhookVerificationResult,
    AbstractNewsBackend
)

__all__ = (
    'NewsArticle',
    'NewsFetchResult',
    'WebhookVerificationResult',
    'AbstractNewsBackend'
)
