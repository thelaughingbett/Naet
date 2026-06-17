from base.modules.socials.news.registry import news_registry
from celery import shared_task

from base.models import NewsItem


@shared_task
def sync_news_feeds():
    """
    Runs on a schedule. Pulls from all registered backends
    and upserts into NewsItem — deduplication via external_id.
    """
    for name, backend in news_registry.all().items():
        result = backend.fetch(limit=20)

        if not result.success:
            # log and continue — don't let one bad backend kill the rest
            print(f"[news] {name} fetch failed: {result.message}")
            continue

        for article in result.articles:
            NewsItem.objects.update_or_create(
                external_id=article.external_id,
                defaults={
                    'title':       article.title,
                    'summary':     article.summary,
                    'category':    article.category,
                    'date':        article.date,
                    'source_url':  article.source_url,
                    'source_name': article.source_name,
                    'badge':       article.badge,
                    'thumbnail':   article.thumbnail,
                }
            )
