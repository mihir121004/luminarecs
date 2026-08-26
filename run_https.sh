#!/bin/zsh
# =============================================================
# HTTPS development server for LuminaRecs
#
# Serves Django directly over TLS using django-extensions'
# runserver_plus (Werkzeug) with the self-signed certificate
# in certs/. Code autoreload stays enabled.
#
# Usage:   ./run_https.sh        -> https://localhost:8000
#          ./run_https.sh 8443   -> custom port
#
# The first visit will show a browser warning because the
# certificate is self-signed. Click through it once per
# browser, or double-click certs/localhost.pem in Keychain
# Access and set "Always Trust" to remove the warning.
# =============================================================

PORT="${1:-8000}"
cd "$(dirname "$0")" || exit 1

exec venv/bin/python manage.py runserver_plus \
  --cert-file certs/localhost.pem \
  --key-file certs/localhost-key.pem \
  "127.0.0.1:${PORT}"
