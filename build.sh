#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files (skip if no static files)
python manage.py collectstatic --no-input || true

# Run migrations
python manage.py migrate
