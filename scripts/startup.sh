#!/bin/bash

# Azure App Service startup script for ScalperToday API

# Add src to Python path so scalper_today package is importable
export PYTHONPATH="/home/site/wwwroot/src:$PYTHONPATH"

# Create data directory for SQLite database
mkdir -p /home/site/wwwroot/data

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Start with gunicorn using the root app.py entry point
# - 1 worker (free tier F1 has limited resources)
# - app:app references the root app.py which handles PYTHONPATH
gunicorn app:app \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
