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
class NewsArticle:
    """
    The normalised shape of a news article from any source.

    Integrators return this from fetch() — Naet doesn't care
    whether it came from WordPress, a custom CMS, or an RSS feed.
    """
    external_id:  str                        # unique ID in the source system
    title:        str
    summary:      str                        # 1-2 sentences for the card
    category:     str                        # "Achievement", "Sports", etc.
    date:         datetime.date
    source_url:   str                        # → redirect to full article
    # "University Website", "KBC", etc.
    source_name:  str

    badge:        Optional[str] = None       # "🏆 Milestone", "⭐ Featured"
    thumbnail:    Optional[str] = None       # image URL
    raw:          Optional[dict] = None      # full raw payload for debugging


@dataclass
class NewsFetchResult:
    """
    Returned by every news backend after fetching articles.
    """
    success:  bool
    articles: list[NewsArticle] = field(default_factory=list)
    message:  str = ""
    raw:      Optional[dict] = None


@dataclass
class WebhookVerificationResult:
    """
    Returned after verifying an inbound push from a CMS.
    """
    valid:    bool
    article:  Optional[NewsArticle] = None
    message:  str = ""
    raw:      Optional[dict] = None


class AbstractNewsBackend(ABC):
    """
    Contract every news source must implement.

    Integrators subclass this and implement fetch() and verify_webhook().
    Naet handles storage, deduplication, and display.

    Example implementations:
        - WordPressNewsBackend   → polls /wp-json/wp/v2/posts
        - RSSNewsBackend         → parses an RSS/Atom feed
        - CMSWebhookBackend      → accepts push from a custom CMS
        - StaticNewsBackend      → reads from a local JSON file (testing)

    Usage in settings.py:
        NEWS_BACKEND = 'myapp.integrations.news.WordPressNewsBackend'
    """

    # override in subclass — shown in admin/logs
    source_name: str = ""

    @abstractmethod
    def fetch(self, limit: int = 20) -> NewsFetchResult:
        """
        Pull the latest articles from the source.

        Called by the Celery beat task on a schedule.
        Return NewsFetchResult with as many NewsArticle objects as available.

        Do NOT save anything here — just fetch and normalise.
        Naet will call update_or_create on external_id for deduplication.

        Raise nothing — catch your own exceptions and return
        NewsFetchResult(success=False, message=str(e)) instead.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        Parse and verify an inbound webhook push from the CMS.

        Verify the signature (shared secret, HMAC, etc.).
        Parse the payload into a NewsArticle.
        Return valid=False if signature check fails — Naet will 400 the request.

        Do NOT save anything here.
        """
        raise NotImplementedError

    def get_webhook_url_name(self) -> str:
        """
        Named URL for this backend's inbound webhook endpoint.
        Default: 'webhook-news-{source_name}'
        Override if needed.
        """
        return f'webhook-news-{self.source_name.lower().replace(" ", "-")}'
