FROM python:3.14-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY chartist/ /app/

# Expose the application port
EXPOSE 8000

# Create a script to determine which service to run
RUN echo '#!/bin/bash\n\
if [ "$SERVICE_TYPE" = "worker" ]; then\n\
    echo "Starting Celery worker..."\n\
    cd /app && celery -A app.tasks.analysis_tasks:celery_app worker --loglevel=info --concurrency=1\n\
elif [ "$SERVICE_TYPE" = "beat" ]; then\n\
    echo "Starting Celery beat..."\n\
    cd /app && celery -A app.tasks.analysis_tasks:celery_app beat --loglevel=info\n\
else\n\
    echo "Starting FastAPI server..."\n\
    gunicorn -k uvicorn.workers.UvicornWorker app.main:app --workers "${GUNICORN_WORKERS:-2}" --bind 0.0.0.0:8000 --timeout 60 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50\n\
fi' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Default command
CMD ["/app/entrypoint.sh"]
