#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Gunicorn production tuning:
#   --workers/threads         bounded concurrency for 4GB-class VMs
#   --max-requests + jitter   recycle workers to cap memory growth
#   --timeout                 kill stuck requests (ML inference can be slow;
#                             kept generous but finite)
#   --limit-request-line      reject absurd request lines cheaply
exec gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --worker-tmp-dir /dev/shm \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 500 \
  --max-requests-jitter 50 \
  --limit-request-line 8190 \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-172.16.0.0/12}" \
  --access-logfile - \
  --error-logfile -