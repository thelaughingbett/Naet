from django.urls import include, path
from .views import invoice_pdf


urlpatterns = [
    path('pdf/', invoice_pdf)
]
