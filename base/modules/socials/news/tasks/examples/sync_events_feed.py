from celery import shared_task
import requests

from django.conf import settings

from base.models import EventItem


@shared_task
def sync_events_feed():
    events = requests.get(settings.EVENTS_FEED_URL).json()
    for item in events:
        EventItem.objects.update_or_create(
            external_id=item['id'],
            defaults={}
        )
