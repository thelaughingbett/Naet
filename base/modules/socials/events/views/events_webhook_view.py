# events/views.py
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from base.modules.socials.events.registry import events_registry
from base.modules.socials.events.sync import upsert_event, unpublish_event


@method_decorator(csrf_exempt, name='dispatch')
class EventsWebhookView(View):
    """
    POST /events/webhook/<source_name>/
    CMS pushes here when an event is created, updated, or cancelled.
    """

    def post(self, request, source_name):
        backend = events_registry.get(source_name)
        if not backend:
            return JsonResponse({'error': 'Unknown source'}, status=404)

        result = backend.verify_webhook(request)
        if not result.valid:
            return JsonResponse({'error': result.message}, status=400)

        event = result.event
        if not event:
            return JsonResponse({'error': 'No event in payload'}, status=400)

        if result.action == 'delete':
            unpublish_event(event.external_id)
            return JsonResponse({'status': 'unpublished'})

        upsert_event(event)
        return JsonResponse({'status': 'ok'})
