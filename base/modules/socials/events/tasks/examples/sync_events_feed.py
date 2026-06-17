from celery import shared_task
from base.modules.socials.events.registry import events_registry
from base.modules.socials.events.sync import upsert_event


@shared_task
def sync_event_feeds():
    """
    Runs on a schedule. Pulls from all registered backends and
    upserts into EventItem — deduplication via external_id.
    """
    for name, backend in events_registry.all().items():
        result = backend.fetch(limit=50, upcoming_only=True)

        if not result.success:
            # log and continue — don't let one bad backend kill the rest
            print(f"[events] {name} fetch failed: {result.message}")
            continue

        for event in result.events:
            upsert_event(event)
