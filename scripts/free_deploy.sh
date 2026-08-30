#!/bin/sh
# ==========================================================================
# FREE PUBLIC DEPLOYMENT — Cloudflare quick tunnel (no account, no card)
#
#   ./scripts/free_deploy.sh          # start  -> prints public HTTPS URL
#   ./scripts/free_deploy.sh stop     # stop both processes
#
# What it does:
#   1. Starts a production gunicorn (DEBUG=False, boot guard enforced) on
#      port 8010 — your dev server on 8000 keeps running untouched.
#   2. Starts a Cloudflare quick tunnel and reads the generated URL.
#   3. Restarts gunicorn with that exact URL whitelisted in ALLOWED_HOSTS
#      (wildcards are forbidden by the production boot guard).
#
# Logs: /tmp/lum_gunicorn.log and /tmp/cf_tunnel.log
# NOTE: quick-tunnel URLs rotate every restart. For a stable URL use a
#       named tunnel with your own domain (see docs/FREE_DEPLOYMENT.md).
# ==========================================================================
set -e
cd "$(dirname "$0")/.."
PORT=8010
LOG_GUNI=/tmp/lum_gunicorn.log
LOG_CF=/tmp/cf_tunnel.log

CF="${CF:-/tmp/cloudflared}"
[ -x "$CF" ] || CF="$(command -v cloudflared || echo /opt/homebrew/bin/cloudflared)"

case "${1:-start}" in
  stop)
    pkill -f "gunicorn core.wsgi:application --bind 127.0.0.1:$PORT" 2>/dev/null || true
    pkill -f "cloudflared tunnel --url http://localhost:$PORT" 2>/dev/null || true
    echo "stopped (gunicorn + tunnel)"
    exit 0
    ;;
esac

if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
  echo "ERROR: port $PORT already in use — run './scripts/free_deploy.sh stop' first."
  exit 1
fi

# 1. tunnel first so we know the public URL before whitelisting it
nohup "$CF" tunnel --url "http://localhost:$PORT" > "$LOG_CF" 2>&1 &
sleep 9
URL="$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_CF" | head -1)"
[ -n "$URL" ] || { echo "ERROR: tunnel failed:"; tail -5 "$LOG_CF"; exit 1; }

# 2. production gunicorn, whitelisting exactly this host (no wildcards)
nohup env DEBUG=False TRUST_PROXY=True SECURE_HSTS_SECONDS=31536000 \
  ALLOWED_HOSTS="${URL#https://},localhost,127.0.0.1" \
  CSRF_TRUSTED_ORIGINS="$URL" \
  venv/bin/gunicorn core.wsgi:application \
    --bind "127.0.0.1:$PORT" --workers 1 --threads 4 --timeout 120 \
    --access-logfile - --error-logfile - > "$LOG_GUNI" 2>&1 &
sleep 10

CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 90 "http://127.0.0.1:$PORT/")"
[ "$CODE" = "200" ] || { echo "ERROR: app returned HTTP $CODE:"; tail -5 "$LOG_GUNI"; exit 1; }

echo ""
echo "  LIVE: $URL"
echo "  stop: ./scripts/free_deploy.sh stop"
echo ""
