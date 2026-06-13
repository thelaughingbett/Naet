from django.urls import path

from base.views import (
    FeeStatementView,
    PaymentView,
    PaymentConfigView,
    PaymentStatusView
)

urlpatterns = [
    path('fees/',      FeeStatementView.as_view(), name='base-fee-statement'),
    path('fees/pay/',  PaymentView.as_view(),       name='base-payment'),
    path('fees/pay/config/',
         PaymentConfigView.as_view(),
         name='payment-config'
         ),
    path('fees/pay/status/<uuid:payment_id>/',
         PaymentStatusView.as_view(),
         name='payment-status'
         ),
]
