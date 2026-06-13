import datetime
import logging
from typing import Optional
from news.backends.base import AbstractNewsBackend, NewsFetchResult, NewsArticle, WebhookVerificationResult

logger = logging.getLogger(__name__)


class WordPressNewsBackend(AbstractNewsBackend):
    """
    Core backend tool to pull article cards from a WordPress site.
    """
    # This name becomes the unique registry key: "wordpress-blog"
    source_name: str = "WordPress Blog"

    def fetch(self, limit: int = 20) -> NewsFetchResult:
        """
        Pull the newest post data items from the WordPress API.
        """
        try:
            # Imagine a web client here getting data from: /wp-json/wp/v2/posts
            mock_payload = [
                {
                    "id": "wp-101",
                    "title": {"rendered": "University Wins Top Innovation Award"},
                    "excerpt": {"rendered": "Our research team took home the grand prize this week."},
                    "categories": ["Achievement"],
                    "link": "https://example.com",
                    "date": "2026-06-12"
                }
            ]

            clean_articles = []
            for item in mock_payload[:limit]:
                # Extract simple raw title and summary text strings
                raw_title = item.get("title", {}).get("rendered", "No Title")
                raw_summary = item.get("excerpt", {}).get("rendered", "")

                # Parse date string cleanly
                date_str = item.get("date", "")
                parsed_date = datetime.date.fromisoformat(
                    date_str) if date_str else datetime.date.today()

                # Build our standardized data shape
                article = NewsArticle(
                    external_id=str(item.get("id")),
                    title=raw_title,
                    summary=raw_summary,
                    category=item.get("categories", ["General"])[0],
                    date=parsed_date,
                    source_url=item.get("link", ""),
                    source_name=self.source_name,
                    raw=item  # Save raw dictionary payload for debugging logs
                )
                clean_articles.append(article)

            return NewsFetchResult(success=True, articles=clean_articles)

        except Exception as e:
            logger.error(f"Failed to fetch from {self.source_name}: {str(e)}")
            # Catch exceptions locally as ordered by the contract rules
            return NewsFetchResult(success=False, message=str(e))

    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        Confirm an inbound push alert payload from WordPress.
        """
        try:
            # Imagine reading a secret token key out of the request headers
            auth_header = request.headers.get("X-WP-Webhook-Secret", "")

            if auth_header != "super-secret-key-phrase":
                return WebhookVerificationResult(valid=False, message="Invalid signature token")

            # Parse out the data payload to save it safely
            # Note: We do NOT write to the database here!
            return WebhookVerificationResult(valid=True, message="Webhook checked out successfully")

        except Exception as e:
            return WebhookVerificationResult(valid=False, message=str(e))
