
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('financial_ledger')

# Load task modules from all registered Django apps
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule for Periodic Tasks
app.conf.beat_schedule = {
    'reconcile-daily-transactions': {
        'task': 'ledger.tasks.reconcile_daily_transactions',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
    'generate-daily-reports': {
        'task': 'ledger.tasks.generate_daily_reports',
        'schedule': crontab(hour=3, minute=0),  # Run at 3 AM daily
    },
    'cleanup-old-logs': {
        'task': 'ledger.tasks.cleanup_old_logs',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Run weekly on Sunday at 4 AM
    },
    'sync-payment-gateway-status': {
        'task': 'payments.tasks.sync_payment_gateway_status',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')