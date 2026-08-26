#!/bin/sh
# ==========================================================================
# LuminaRecs secure deployment script
#
#   ./scripts/deploy.sh              validate .env, build & start the stack
#   ./scripts/deploy.sh --firewall   also configure a deny-by-default UFW
#                                    firewall (run once, as root, with ufw
#                                    installed)
#
# Safety properties:
#   * Refuses to deploy if any required secret is missing/weak.
#   * Refuses to deploy with DEBUG=True (would silently disable every
#     transport-security control).
#   * Firewall denies everything except SSH/HTTP/HTTPS.
# ==========================================================================
set -eu

cd "$(dirname "$0")/.."

# ------------------------------------------------------- firewall mode ----
if [ "${1:-}" = "--firewall" ]; then
  [ "$(id -u)" = "0" ] || fail "Run --firewall as root (sudo ./scripts/deploy.sh --firewall)"
  command -v ufw >/dev/null || fail "ufw not installed (apt install ufw)."
  ufw default deny incoming
  ufw default allow outgoing
  # Docker bypasses UFW for published ports, so restrict what containers expose:
  # only caddy publishes 80/443 (db/redis/web publish nothing by design).
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  yes | ufw enable
  ok "Firewall active: only SSH/HTTP/HTTPS allowed inbound."
  ufw status verbose
  exit 0
fi

fail() { printf '\n\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$1"; }
warn() { printf '\033[33m! %s\033[0m\n' "$1"; }

[ -f .env ] || fail ".env not found. Run: cp .env.example .env  then fill it in."
set -a; . ./.env; set +a

# ---------------------------------------------------------------- checks --
[ "${DEBUG:-True}" = "False" ] || fail "DEBUG must be False in production (it disables HSTS/SSL-redirect/secure-cookies)."
[ -n "${SECRET_KEY:-}" ] || fail "SECRET_KEY is empty."
case "${SECRET_KEY:-}" in *django-insecure*) fail "SECRET_KEY is still a 'django-insecure-*' dev key."; esac
[ ${#SECRET_KEY} -ge 50 ] || warn "SECRET_KEY shorter than 50 chars — recommended to regenerate with token_urlsafe(64)."
[ -n "${DOMAIN:-}" ] || fail "DOMAIN is empty (needed by Caddy for HTTPS certificates)."
[ -n "${ALLOWED_HOSTS:-}" ] || fail "ALLOWED_HOSTS is empty."
[ -n "${DB_PASSWORD:-}" ] && [ ${#DB_PASSWORD} -ge 16 ] || fail "DB_PASSWORD must be at least 16 characters."
[ -n "${MYSQL_ROOT_PASSWORD:-}" ] && [ ${#MYSQL_ROOT_PASSWORD} -ge 16 ] || fail "MYSQL_ROOT_PASSWORD must be at least 16 characters."
[ -n "${REDIS_PASSWORD:-}" ] && [ ${#REDIS_PASSWORD} -ge 16 ] || fail "REDIS_PASSWORD must be at least 16 characters."
if [ -n "${EMAIL_HOST_USER:-}" ]; then
  [ -n "${EMAIL_HOST_PASSWORD:-}" ] || warn "EMAIL_HOST_USER set but EMAIL_HOST_PASSWORD empty — password-reset mail will fail."
fi
[ -x /usr/bin/docker ] || command -v docker >/dev/null || fail "Docker is not installed. curl -fsSL https://get.docker.com | sh"

# ---------------------------------------------------------------- deploy --
echo ""
echo "Configuration OK. Building & starting the stack..."
docker compose up -d --build

echo ""
docker compose ps

cat <<'EOF'

Next steps:
  1. Watch startup logs:    docker compose logs -f web
  2. Verify DNS points at this server, then open https://$DOMAIN
     (Caddy obtains the TLS certificate automatically on first request)
  3. Create a superuser:    docker compose exec web python manage.py createsuperuser
  4. First-time hardening:  sudo ./scripts/deploy.sh --firewall
EOF