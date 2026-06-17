import os
from celery import Celery

# 1. Point to your Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Naet.settings')

app = Celery('Naet')

# 2. CRITICAL: The namespace='CELERY' forces Celery to look for settings
# that begin with the "CELERY_" prefix in your settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# 3. Load tasks from all registered Django apps
app.autodiscover_tasks()
