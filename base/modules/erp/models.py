# erp/models.py

from base.models import BaseModelMixin
from django.db import models


class ERPSyncLog(BaseModelMixin):

    STATUS_CHOICES = [
        ('attempting', 'Attempting'),
        ('success',    'Success'),
        ('failed',     'Failed'),
        ('error',      'Error'),
        ('exhausted',  'Exhausted'),
    ]

    # generic reference — "Payment:uuid" or "Enrollment:uuid"
    content_type_str = models.CharField(max_length=200)
    event = models.CharField(max_length=100)
    handler = models.CharField(max_length=100)
    attempt = models.IntegerField(default=1)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    message = models.TextField(blank=True)
    external_ref = models.CharField(max_length=100, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.content_type_str} — {self.event} [{self.status}]"
