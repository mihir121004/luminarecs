#!/bin/sh
# ==========================================================================
# DEMO IMAGE ENTRYPOINT (Render free tier / any small container)
#
#   Differences from entrypoint.sh:
#     - SQLite via DB_ENGINE env (no MySQL), locmem cache (no Redis)
#     - Seeds movies from the committed fixture (idempotent)
#     - Auto-configures ALLOWED_HOSTS/CSRF for Render's assigned domain
#     - 1 gunicorn worker to fit 512 MB RAM
# ==========================================================================
set -e

: "${SECRET_KEY:?Set SECRET_KEY (Render: generateValue=true)}"
: "${DEBUG:=False}"
export DEBUG

# Render injects RENDER_EXTERNAL_HOSTNAME (e.g. luminarecs-demo.onrender.com)
: "${ALLOWED_HOSTS:=${RENDER_EXTERNAL_HOSTNAME:-localhost}},127.0.0.1"
export ALLOWED_HOSTS

: "${CSRF_TRUSTED_ORIGINS:=https://${RENDER_EXTERNAL_HOSTNAME:-localhost}}"
export CSRF_TRUSTED_ORIGINS

# Render's edge proxies terminate TLS; the service is unreachable except
# through Render's ingress, so trusting all proxy IPs here is acceptable.
: "${FORWARDED_ALLOW_IPS:=*}"
export FORWARDED_ALLOW_IPS

# No SMTP on the demo: password-reset mail prints to the container log.
: "${EMAIL_BACKEND:=django.core.mail.backends.console.EmailBackend}"
export EMAIL_BACKEND

# Production security flags (boot guard refuses DEBUG=False without these;
# Render passes none of them, so defaults apply).
: "${SECURE_SSL_REDIRECT:=True}"
: "${SECURE_HSTS_SECONDS:=31536000}"
: "${SECURE_HSTS_INCLUDE_SUBDOMAINS:=True}"
: "${SECURE_HSTS_PRELOAD:=True}"
: "${SESSION_COOKIE_SECURE:=True}"
: "${CSRF_COOKIE_SECURE:=True}"
export SECURE_SSL_REDIRECT SECURE_HSTS_SECONDS SECURE_HSTS_INCLUDE_SUBDOMAINS \
       SECURE_HSTS_PRELOAD SESSION_COOKIE_SECURE CSRF_COOKIE_SECURE

# Demo storage: SQLite + locmem cache — no MySQL/Redis services needed.
# (Without CACHE_BACKEND, settings would default to Redis and the
# rate-limit middleware would 500 on every request.)
: "${DB_ENGINE:=django.db.backends.sqlite3}"
: "${DB_NAME:=/tmp/luminarecs_demo.sqlite3}"
: "${CACHE_BACKEND:=locmem}"
export DB_ENGINE DB_NAME CACHE_BACKEND

# Render terminates TLS and forwards plain HTTP: trust its proxy headers
# (required together with SECURE_SSL_REDIRECT=True by the boot guard).
: "${TRUST_PROXY:=True}"
export TRUST_PROXY

: "${GUNICORN_WORKERS:=1}"
: "${GUNICORN_THREADS:=4}"
: "${GUNICORN_TIMEOUT:=120}"
export GUNICORN_WORKERS GUNICORN_THREADS GUNICORN_TIMEOUT

echo "Running migrations (SQLite)..."
python manage.py migrate --noinput

echo "Seeding demo data (movies + genres)..."
python manage.py seed_demo

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --threads "$GUNICORN_THREADS" \
  --worker-tmp-dir /tmp \
  --timeout "$GUNICORN_TIMEOUT" \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 500 \
  --max-requests-jitter 50 \
  --limit-request-line 8190 \
  --forwarded-allow-ips "$FORWARDED_ALLOW_IPS" \
  --access-logfile - \
  --error-logfile -
