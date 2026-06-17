# base/modules/news/views.py
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from base.modules.socials.news.registry import news_registry
from base.models import NewsItem


@method_decorator(csrf_exempt, name='dispatch')
class NewsWebhookView(View):
    """
    POST /news/webhook/<source_name>/
    CMS pushes article here when published/updated.
    """

    def post(self, request, source_name):
        backend = news_registry.get(source_name)
        if not backend:
            return JsonResponse({'error': 'Unknown source'}, status=404)

        result = backend.verify_webhook(request)
        if not result.valid:
            return JsonResponse({'error': result.message}, status=400)

        article = result.article
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
        return JsonResponse({'status': 'ok'})
