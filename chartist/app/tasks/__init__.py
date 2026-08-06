# Tasks package
# No explicit imports here to avoid circular imports

# Import all task modules for Celery to discover them
from app.tasks import analysis_tasks
from app.tasks import news_tasks

# This ensures that tasks are registered with the Celery app when this package is imported
