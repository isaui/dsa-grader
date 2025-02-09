#!/bin/bash

# Log untuk debugging
echo "Starting application with:"
echo "PORT: $PORT"
echo "GRADER_WORKERS: $GRADER_WORKERS"

# Set default values
WORKERS=${GRADER_WORKERS:-2}
PORT=${PORT:-8080}
GUNICORN_WORKERS=${WEB_CONCURRENCY:-2}  # web workers
GUNICORN_THREADS=${THREADS:-4}
TIMEOUT=${TIMEOUT:-60}

# Log configuration
echo "Starting $WORKERS grader workers..."
echo "Starting web server with:"
echo "- Web Workers: $GUNICORN_WORKERS"
echo "- Threads: $GUNICORN_THREADS"
echo "- Timeout: $TIMEOUT"

# Start grader workers
python manage.py run_grader --workers $WORKERS &

# Start web server
gunicorn grader.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers $GUNICORN_WORKERS \
    --threads $GUNICORN_THREADS \
    --timeout $TIMEOUT \
    --access-logfile - \
    --error-logfile - \
    --log-level info