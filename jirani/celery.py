import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jirani.settings')

app = Celery('jirani')

# read config from Django settings (CELERY_ prefix)
app.config_from_object('django.conf:settings', namespace='CELERY')

# auto-discover tasks in all apps
app.autodiscover_tasks()