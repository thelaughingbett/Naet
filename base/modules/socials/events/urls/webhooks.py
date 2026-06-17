from django.urls import path
from base.modules.socials.events.views import EventsWebhookView

urlpatterns = [
    path('webhook/<str:source_name>/',
         EventsWebhookView.as_view(), name='events-webhook'),
]
