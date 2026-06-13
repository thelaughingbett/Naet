# tasks.py
from celery import shared_task
import requests

from django.conf import settings

from base.models import NewsItem


@shared_task
def sync_news_feed():
    feed = requests.get(settings.NEWS_FEED_URL).json()  # or parse RSS
    for item in feed['articles']:
        NewsItem.objects.update_or_create(
            external_id=item['id'],
            defaults={
                'title':      item['title'],
                'summary':    item['summary'],
                'source_url': item['url'],

            }
        )
