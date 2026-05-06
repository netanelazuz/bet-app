#!/bin/sh
set -eu

echo "Waiting for database and applying migrations..."
flask db upgrade

echo "Starting BET app with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers "${GUNICORN_WORKERS:-2}" --threads "${GUNICORN_THREADS:-2}" --timeout "${GUNICORN_TIMEOUT:-60}" run:app
