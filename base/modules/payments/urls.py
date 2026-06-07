from django.urls import path
from .views import PaymentWebhookView, PaymentInitiateView

urlpatterns = [
    path(
        'initiate/',
        PaymentInitiateView.as_view(),
        name='payment-initiate'
    ),
    path(
        'webhook/<str:method>/',
        PaymentWebhookView.as_view(),
        name='payment-webhook'
    ),
]
