#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🎬 Preparing Django database..."
# Run migrations & seed data during startup (where network access to Neon is guaranteed)
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_data

echo "🧠 Starting Celery Worker..."
celery -A aec_cinemas worker --loglevel=info &

echo "⏰ Starting Celery Beat..."
celery -A aec_cinemas beat --loglevel=info &

echo "🚀 Starting Gunicorn Web Server..."
gunicorn aec_cinemas.wsgi:application
