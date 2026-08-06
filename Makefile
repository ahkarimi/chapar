PYTHON ?= python

.PHONY: help install env bot api worker beat test up down clean

help:
	@echo "Chapar"
	@echo ""
	@echo "  make install  Install all Python dependencies"
	@echo "  make env      Create .env from .env.example if absent"
	@echo "  make bot      Run the Telegram bot"
	@echo "  make api      Run the FastAPI service"
	@echo "  make worker   Run the Celery worker"
	@echo "  make beat     Run the Celery scheduler"
	@echo "  make test     Run project tests"
	@echo "  make up       Start the Docker stack"
	@echo "  make down     Stop the Docker stack"
	@echo "  make clean    Remove Python and pytest caches"

install:
	$(PYTHON) -m pip install -r requirements.txt

env:
	test -f .env || cp .env.example .env

bot:
	cd bot && $(PYTHON) bot.py

api:
	cd chartist && $(PYTHON) -m uvicorn app.main:app --reload

worker:
	cd chartist && $(PYTHON) -m celery -A app.tasks.analysis_tasks:celery_app worker --loglevel=info --concurrency=1

beat:
	cd chartist && $(PYTHON) -m celery -A app.tasks.analysis_tasks:celery_app beat --loglevel=info

test:
	$(PYTHON) -m pytest -q

up:
	docker compose up --build

down:
	docker compose down

clean:
	find bot chartist -type d -name "__pycache__" -prune -exec rm -rf {} +
	find bot chartist -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find bot chartist -type f -name "*.pyc" -delete
