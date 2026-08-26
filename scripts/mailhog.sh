#!/usr/bin/env bash
# =============================================================
# MailHog launcher for LuminaRecs local development.
#
# MailHog is a small SMTP server / mail catcher. When the app's
# EMAIL_BACKEND points at SMTP 127.0.0.1:1025 (see .env), every
# email the app "sends" — including password-reset links — is
# captured here and shown in a local web UI instead of being
# lost or delivered for real.
#
#   Web UI  (view captured mail):  http://127.0.0.1:8025
#   SMTP      (app sends to this): 127.0.0.1:1025
#
# Run it in a terminal (keep it running while the server runs):
#   ./scripts/mailhog.sh
# =============================================================
set -euo pipefail

# Location for the local MailHog binary (kept out of git).
BIN_DIR="$(cd "$(dirname "$0")/.." && pwd)/scripts/.bin"
BIN="$BIN_DIR/mailhog"
VERSION="v1.0.1"

# Determine the right macOS/Linux binary for this machine.
# NOTE: MailHog v1.0.1 only publishes a darwin_amd64 build. On Apple Silicon
# that runs via Rosetta 2 (macOS will prompt once to install it if missing).
case "$(uname -s):$(uname -m)" in
  Darwin:arm64)  BINARY="MailHog_darwin_amd64" ;;   # runs under Rosetta 2
  Darwin:x86_64) BINARY="MailHog_darwin_amd64" ;;
  Linux:x86_64)  BINARY="MailHog_linux_amd64" ;;
  Linux:arm64)   BINARY="MailHog_linux_amd64" ;;
  *)
    echo "Unsupported platform for scripted download: $(uname -s)/$(uname -m)"
    echo "Install MailHog manually instead (https://github.com/mailhog/MailHog)."
    exit 1 ;;
esac

DOWNLOAD_URL="https://github.com/mailhog/MailHog/releases/download/${VERSION}/${BINARY}"

# Download the binary on first use.
if [ ! -x "$BIN" ]; then
  echo "Downloading MailHog ${VERSION} (${BINARY})..."
  mkdir -p "$BIN_DIR"
  curl -fL --retry 3 -o "$BIN.tmp" "$DOWNLOAD_URL"
  chmod +x "$BIN.tmp"
  mv "$BIN.tmp" "$BIN"
fi

SMTP_ADDR="${MH_SMTP_BIND_ADDR:-127.0.0.1:1025}"
HTTP_ADDR="${MH_API_BIND_ADDR:-127.0.0.1:8025}"

echo "MailHog ready:"
echo "  Web UI (view emails): http://127.0.0.1:8025"
echo "  SMTP (app sends to):  127.0.0.1:1025"
exec "$BIN" \
  -smtp-bind-addr "$SMTP_ADDR" \
  -api-bind-addr  "$HTTP_ADDR" \
  -ui-bind-addr   "$HTTP_ADDR"