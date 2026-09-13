from django.urls import path

from base.views import TicketView

urlpatterns = [
    path('ticket/', TicketView.as_view(),       name='base-ticket'),
]
