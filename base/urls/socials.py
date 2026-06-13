from django.urls import path

from base.views import EventsView, NewsView

urlpatterns = [
    path('events/', EventsView.as_view(), name='base-events'),
    path('news/',   NewsView.as_view(),   name='base-news'),
]
