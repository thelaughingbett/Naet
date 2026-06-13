import datetime
from typing import Optional
from news.backends.base import AbstractNewsBackend, NewsFetchResult, NewsArticle, WebhookVerificationResult


class RSSNewsBackend(AbstractNewsBackend):
    """
    A community-built plugin tool to read standard XML RSS feeds.
    """
    # This name becomes the unique registry key: "global-rss-feed"
    source_name: str = "Global RSS Feed"

    def fetch(self, limit: int = 20) -> NewsFetchResult:
        """
        Read raw XML channel content data and shape it into cards.
        """
        try:
            # Imagine using an XML reader to extract items from a feed link
            mock_xml_items = [
                {
                    "guid": "rss-99",
                    "title": "Track Team Wins Gold Medal",
                    "description": "Our sports stars set a new record high score.",
                    "category": "Sports",
                    "link": "https://kbc-news.example",
                    "pubDate": "2026-06-12"
                }
            ]

            clean_articles = []
            for item in mock_xml_items[:limit]:
                article = NewsArticle(
                    external_id=str(item.get("guid")),
                    title=item.get("title", "Untitled"),
                    summary=item.get("description", ""),
                    category=item.get("category", "General"),
                    date=datetime.date.today(),  # Simplified date look up
                    source_url=item.get("link", ""),
                    source_name=self.source_name,
                    badge="🏆 Milestone" if item.get(
                        "category") == "Sports" else None,
                    raw=item
                )
                clean_articles.append(article)

            return NewsFetchResult(success=True, articles=clean_articles)

        except Exception as e:
            return NewsFetchResult(success=False, message=str(e))

    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        RSS feeds do not have inbound webhooks. 
        We reject inbound webhook calls safely according to our contract.
        """
        return WebhookVerificationResult(
            valid=False,
            message="Webhooks are not supported by the RSS source feed backend."
        )
