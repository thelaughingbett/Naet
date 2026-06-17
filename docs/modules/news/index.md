# 📰 News Module

> How university news and announcements get from wherever they live —
> a WordPress site, an RSS feed, a custom CMS, a webhook push —
> into the student portal. And how to add a new news source without
> touching a single line of core code.
> Think of this as the bulletin board layer — pluggable, institution-agnostic,
> and honest about what it does and doesn't store.

---

## 🗺️ Overview

Naet doesn't try to be a CMS. It's not trying to replace your university's
news website. It's trying to show students the headlines, with a link back
to wherever the full article lives.

```
External source (WordPress, RSS, custom CMS, webhook, manual admin entry)
      ↓
AbstractNewsBackend.fetch()        ← your backend normalises it
      ↓
NewsItem stored in DB              ← or rendered directly if no DB rows yet
      ↓
NewsView queries NewsItem          ← student sees a card + "Read more →" link
      ↓
Student clicks "Read more →"       ← redirected to source_url (the real article)
```

Naet stores **card data only** — title, summary, category, date, badge, and
the `source_url` that points to the full article. It never duplicates the full
article content. This keeps the system simple and keeps copyright where it belongs.

---

## 🏗️ Architecture

```
base/modules/news/
├── backends/
│   ├── __init__.py       # exports AbstractNewsBackend + dataclasses
│   ├── base.py           # the contract
│   └── contrib/          # community-contributed backends
│       └── README.md
├── registry.py           # NewsRegistry singleton
├── tasks.py              # Celery beat task: sync_news_feeds()
├── urls.py               # webhook routing
└── views.py              # NewsWebhookView
```

---

## 🔄 The Two Modes

| Mode                      | When                                                    | How                                                                                                 |
| ------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Model-backed** (Mode A) | Backends registered + Celery running                    | Sync task runs every 30 min, stores into `NewsItem` — fast, filterable, full-text searchable via DB |
| **Live** (Mode B)         | Backends registered, no Celery / no `NewsItem` rows yet | `NewsView` calls `backend.fetch()` on each request — slower but zero DB setup                       |
| **Manual**                | No backends registered, admin adds news directly        | `NewsItem` rows created in Django admin — same result as Mode A from the view's perspective         |

The view checks `NewsItem.objects.exists()` and falls through to Mode B
automatically if no rows exist. No config flag needed.

---

## 📐 The Contract

```python
class AbstractNewsBackend(ABC):

    source_name: str = ""   # shown in admin/logs, used as webhook route key

    @abstractmethod
    def fetch(self, limit: int = 20) -> NewsFetchResult:
        """
        Pull the latest articles from the source.
        Normalise them into NewsArticle dataclasses.
        Called by the Celery task on a schedule.

        DO NOT save anything here — just fetch and normalise.
        Catch all exceptions internally.
        Return NewsFetchResult(success=False, message=str(e)) on failure.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        Parse and verify an inbound push from the CMS.
        Verify the signature. Parse the payload into a NewsArticle.
        Return valid=False if verification fails.

        DO NOT save anything here.
        """
        raise NotImplementedError
```

### 📦 The dataclasses

| Dataclass                   | Purpose                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------- |
| `NewsArticle`               | The normalised shape of one article — title, summary, category, date, `source_url` |
| `NewsFetchResult`           | Wraps a list of `NewsArticle` objects + success/failure info                       |
| `WebhookVerificationResult` | Result of verifying a CMS push — includes the parsed `NewsArticle`                 |

### 🔑 Key fields on `NewsArticle`

```python
@dataclass
class NewsArticle:
    external_id:  str           # unique ID in the source system
    title:        str
    summary:      str           # 1-2 sentences — enough for the card
    category:     str           # "Achievement", "Academic", "Sports", etc.
    date:         datetime.date
    source_url:   str           # → redirect to full article (required)
    source_name:  str           # "University Website", "KBC", etc.

    badge:        Optional[str] = None      # "🏆 Milestone", "⭐ Featured"
    thumbnail:    Optional[str] = None      # image URL for the card
    raw:          Optional[dict] = None     # full raw payload for debugging
```

> 💡 `source_url` is non-negotiable. It's what makes the whole thing
> institution-agnostic. One school redirects to WordPress, another to
> their custom CMS, another to a PDF notice — Naet doesn't care.

---

## 🛠️ Adding a New Backend

### Step 1 — Decide where your file lives

Community contribution:

```
base/modules/news/backends/contrib/wordpress.py
```

Institution-specific:

```
base/modules/news/backends/wordpress.py
```

### Step 2 — Implement the contract

Here's a complete WordPress backend as an example:

```python
# base/modules/news/backends/wordpress.py

import requests
import datetime
from django.conf import settings

from base.modules.news.backends import (
    AbstractNewsBackend,
    NewsArticle,
    NewsFetchResult,
    WebhookVerificationResult,
)


class WordPressNewsBackend(AbstractNewsBackend):
    """
    Pulls articles from a WordPress site via the WP REST API.
    https://developer.wordpress.org/rest-api/reference/posts/

    Settings required:
        WORDPRESS_URL = "https://news.university.ac.ke"
    """

    source_name = "wordpress"

    def fetch(self, limit: int = 20) -> NewsFetchResult:
        try:
            response = requests.get(
                f"{settings.WORDPRESS_URL}/wp-json/wp/v2/posts",
                params={
                    'per_page': limit,
                    '_fields':  'id,title,excerpt,date,link,categories,tags',
                },
                timeout=10,
            )
            response.raise_for_status()
            posts = response.json()

        except Exception as e:
            return NewsFetchResult(success=False, message=str(e))

        articles = []
        for post in posts:
            articles.append(NewsArticle(
                external_id=  str(post['id']),
                title=        post['title']['rendered'],
                summary=      _strip_html(post['excerpt']['rendered']),
                category=     _resolve_category(post.get('categories', [])),
                date=         datetime.date.fromisoformat(post['date'][:10]),
                source_url=   post['link'],
                source_name=  self.source_name,
                raw=          post,
            ))

        return NewsFetchResult(success=True, articles=articles)

    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        WordPress doesn't have native webhooks — this handles
        WP Webhooks plugin or similar.
        """
        import hmac, hashlib, json
        from django.conf import settings

        secret    = getattr(settings, 'WORDPRESS_WEBHOOK_SECRET', '')
        signature = request.headers.get('X-WP-Webhook-Signature', '')

        try:
            body = request.body
            expected = hmac.new(
                secret.encode(), body, hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                return WebhookVerificationResult(valid=False, message='Invalid signature')

            payload = json.loads(body)
            post    = payload.get('post', {})

            article = NewsArticle(
                external_id=  str(post['ID']),
                title=        post['post_title'],
                summary=      _strip_html(post.get('post_excerpt', post['post_content'][:300])),
                category=     post.get('category', 'General'),
                date=         datetime.date.fromisoformat(post['post_date'][:10]),
                source_url=   post['guid'],
                source_name=  self.source_name,
                raw=          payload,
            )

            return WebhookVerificationResult(valid=True, article=article)

        except Exception as e:
            return WebhookVerificationResult(valid=False, message=str(e))


def _strip_html(html: str) -> str:
    """Remove HTML tags from WordPress excerpts."""
    import re
    clean = re.sub(r'<[^>]+>', '', html)
    return clean.strip()


def _resolve_category(category_ids: list) -> str:
    """
    Map WordPress category IDs to human-readable names.
    Extend this with a settings map or an API call if needed.
    """
    CATEGORY_MAP = getattr(settings, 'WORDPRESS_CATEGORY_MAP', {})
    for cid in category_ids:
        if str(cid) in CATEGORY_MAP:
            return CATEGORY_MAP[str(cid)]
    return 'General'
```

### Step 3 — Register it

```python
# base/apps.py
class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        import base.utils.receivers   # signals

        from base.modules.news.registry import news_registry
        from base.modules.news.backends.wordpress import WordPressNewsBackend

        news_registry.register(WordPressNewsBackend())
```

### Step 4 — Add settings

```python
# settings.py (or .env)
WORDPRESS_URL             = "https://news.university.ac.ke"
WORDPRESS_WEBHOOK_SECRET  = "your-shared-secret-here"
WORDPRESS_CATEGORY_MAP    = {
    "3": "Academic",
    "5": "Achievement",
    "7": "Scholarship",
}
```

### Step 5 — (Optional) Enable the Celery sync task

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'sync-news-feeds': {
        'task':     'base.modules.news.tasks.sync_news_feeds',
        'schedule': 60 * 30,   # every 30 minutes
    },
}
```

---

## 🔄 The Sync Flow (Mode A)

```
Celery beat fires every 30 min
      ↓
sync_news_feeds() iterates news_registry.all()
      ↓
backend.fetch(limit=20) called per registered backend
      ↓
Each NewsArticle → NewsItem.update_or_create(external_id=...)
      ↓
NewsView queries NewsItem — always fast, always DB-backed
      ↓
Student sees card with "Read more →" link → source_url
```

Deduplication is entirely driven by `external_id`. If the same article
is fetched twice, it's updated in place — no duplicate cards.

---

## 🔗 Webhook Route

```
POST /news/webhook/<source_name>/
```

Your backend's `source_name` becomes the route segment:

```python
# wordpress backend with source_name = "wordpress"
POST /news/webhook/wordpress/
```

The webhook view calls `backend.verify_webhook(request)`, checks `result.valid`,
then calls `NewsItem.update_or_create(external_id=result.article.external_id, ...)`.

For real-time updates — register this URL with your CMS's webhook settings.
For scheduled pull only — skip the webhook entirely.

---

## 🏫 Manual News (No Backend)

If an institution has no CMS, or just wants to post occasional notices:

```
Admin → Base → News Items → Add News Item
```

Use a namespaced `external_id` to avoid future collisions with a backend:

```
manual:graduation-announcement-2026
manual:fee-deadline-reminder-sem1
```

These will show up identically to backend-synced articles from the student's
perspective.

---

## 🚦 The Golden Rules

**1. Never save anything inside `fetch()` or `verify_webhook()`**
The sync task and the webhook view own all DB writes.
Your backend owns the external API conversation only.

**2. Always return a result dataclass — never raise**
If the CMS is down, return `NewsFetchResult(success=False, message=str(e))`.
The sync task logs it and moves on.

**3. `source_url` is required**
An article without a `source_url` is a dead end for the student.
If your source doesn't provide a URL, use the source's homepage as a fallback
rather than leaving it empty.

**4. `external_id` must be stable**
This is the deduplication key. If your CMS changes IDs (e.g. regenerates
slugs), you'll get duplicate cards. Use the CMS's internal integer ID
rather than slugs wherever possible.

**5. `summary` is card text — not the full article**
Keep it to 1-3 sentences. The full article lives at `source_url`.
Don't try to strip and store the entire article body.

---

## 🧪 Testing your backend

```python
# tests/test_news_backend.py
from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from base.modules.news.backends.wordpress import WordPressNewsBackend


class WordPressBackendTest(TestCase):

    def setUp(self):
        self.backend = WordPressNewsBackend()

    @patch('base.modules.news.backends.wordpress.requests.get')
    def test_fetch_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = [{
            'id':      42,
            'title':   {'rendered': 'University Ranked Top 5'},
            'excerpt': {'rendered': '<p>We are proud to announce...</p>'},
            'date':    '2026-05-28T09:00:00',
            'link':    'https://news.university.ac.ke/ranked-top-5',
            'categories': ['5'],
        }]

        result = self.backend.fetch(limit=10)

        self.assertTrue(result.success)
        self.assertEqual(len(result.articles), 1)

        article = result.articles[0]
        self.assertEqual(article.external_id, '42')
        self.assertEqual(article.title, 'University Ranked Top 5')
        self.assertEqual(article.source_url, 'https://news.university.ac.ke/ranked-top-5')
        self.assertNotIn('<p>', article.summary)   # HTML stripped

    @patch('base.modules.news.backends.wordpress.requests.get')
    def test_fetch_api_down(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")

        result = self.backend.fetch()

        self.assertFalse(result.success)
        self.assertIn('Connection', result.message)
        self.assertEqual(result.articles, [])

    def test_verify_webhook_bad_signature(self):
        factory = RequestFactory()
        request = factory.post(
            '/news/webhook/wordpress/',
            data=b'{"post": {}}',
            content_type='application/json',
            HTTP_X_WP_WEBHOOK_SIGNATURE='badsignature'
        )

        with self.settings(WORDPRESS_WEBHOOK_SECRET='correct-secret'):
            result = self.backend.verify_webhook(request)

        self.assertFalse(result.valid)

    def test_source_name_set(self):
        self.assertEqual(self.backend.source_name, 'wordpress')

    def test_get_form_config_not_required(self):
        # news backends don't need get_form_config — check it doesn't crash
        self.assertTrue(hasattr(self.backend, 'source_name'))
```

---

## 📋 RSS Backend (Bonus Example)

For institutions that expose an RSS feed:

```python
# base/modules/news/backends/contrib/rss.py

import feedparser
import datetime
from base.modules.news.backends import (
    AbstractNewsBackend, NewsArticle, NewsFetchResult, WebhookVerificationResult
)
from django.conf import settings


class RSSNewsBackend(AbstractNewsBackend):
    """
    Pulls articles from any RSS / Atom feed.

    Settings required:
        RSS_FEED_URL = "https://news.university.ac.ke/feed/"
        RSS_CATEGORY = "General"   # default category for all RSS items
    """

    source_name = "rss"

    def fetch(self, limit: int = 20) -> NewsFetchResult:
        try:
            feed = feedparser.parse(settings.RSS_FEED_URL)
            if feed.bozo:
                raise Exception(f"Feed parse error: {feed.bozo_exception}")
        except Exception as e:
            return NewsFetchResult(success=False, message=str(e))

        articles = []
        for entry in feed.entries[:limit]:
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            date = datetime.date(*published[:3]) if published else datetime.date.today()

            articles.append(NewsArticle(
                external_id=  entry.get('id') or entry.get('link'),
                title=        entry.get('title', 'Untitled'),
                summary=      entry.get('summary', '')[:400],
                category=     getattr(settings, 'RSS_CATEGORY', 'General'),
                date=         date,
                source_url=   entry.get('link', ''),
                source_name=  self.source_name,
            ))

        return NewsFetchResult(success=True, articles=articles)

    def verify_webhook(self, request) -> WebhookVerificationResult:
        # RSS doesn't push — webhooks not supported
        return WebhookVerificationResult(valid=False, message="RSS does not support webhooks. Use the fetch() sync instead.")
```

Install `feedparser`:

```bash
pip install feedparser
```

Register:

```python
news_registry.register(RSSNewsBackend())
```

---

## 🔗 Where to Go Next

| Topic                           | Document                         |
| ------------------------------- | -------------------------------- |
| 🎉 Events module (same pattern) | [Events Module](events.md)       |
| 💳 Payments module              | [Payments Module](payments.md)   |
| 🗃️ NewsItem model fields        | [Models Reference](../models.md) |
| 📋 Registry pattern             | `base/modules/news/registry.py`  |
| 🔄 Celery sync task             | `base/modules/news/tasks.py`     |

---

> 🔗 Back to [Documentation Index](../README.md)
