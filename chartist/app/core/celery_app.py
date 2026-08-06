from celery import Celery
import os
from app.config import settings
import importlib

# Create Celery instance - do this first before any task imports
celery_app = Celery(
    "chartist",
    broker=f"{settings.REDIS_URL}/0",
    backend=f"{settings.REDIS_URL}/0"
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes time limit for tasks
    worker_prefetch_multiplier=1,  # Don't prefetch more tasks than workers can handle
    worker_concurrency=4,  # Adjust based on your server capacity
    broker_connection_retry_on_startup=True,  # Fix Celery 6.0 deprecation warning
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'check-expiring-plans-every-3-hours': {
        'task': 'check_expiring_plans',
        'schedule': 10800.0,  # 3 hours in seconds
    },
}

# Set up autodiscovery - this doesn't import modules yet, just sets up paths
celery_app.autodiscover_tasks(["app.tasks"])

# Explicitly import task modules to ensure they're registered
# This is needed because autodiscover may not always work as expected
try:
    # Import the analysis tasks explicitly
    from app.tasks import analysis_tasks
    # Import the news tasks explicitly
    from app.tasks import news_tasks
    # Import the plan tasks explicitly
    from app.tasks import plan_tasks
    print("Successfully imported task modules")
except ImportError as e:
    print(f"Error importing task modules: {e}")

# Print registered tasks at startup to verify configuration
print(f"Registered Celery tasks: {list(celery_app.tasks.keys())}")

# The task modules should only be imported after celery_app is fully defined
# This avoids the circular import problem
