#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$HOME/.config/personal-bio/steam-bridge.json"
read -r -p "Bio page URL [https://example.com]: " BIO_SITE
BIO_SITE="${BIO_SITE:-https://example.com}"
if [[ "$BIO_SITE" != https://* ]]; then
  echo "Please use your HTTPS site address (for example https://example.com)." >&2
  exit 1
fi
read -r -s -p "Paste the connection token from your admin panel: " BIO_TOKEN
echo
if [[ -z "$BIO_TOKEN" ]]; then
  if [[ -f "$CONFIG_PATH" ]]; then
    BIO_TOKEN="$(python3 - "$CONFIG_PATH" <<'PY'
import json
import sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("token", ""))
except (OSError, ValueError):
    pass
PY
)"
  fi
  if [[ -z "$BIO_TOKEN" ]]; then
    echo "Enter the connection token from the admin panel." >&2
    exit 1
  fi
  echo "Reusing the saved connection token."
fi

mkdir -p "$HOME/.config/personal-bio" "$HOME/.local/bin" "$HOME/.config/systemd/user"
BIO_SITE="$BIO_SITE" BIO_TOKEN="$BIO_TOKEN" python3 - "$CONFIG_PATH" <<'PY'
import json
import os
import sys

path = sys.argv[1]
site = os.environ["BIO_SITE"]
token = os.environ["BIO_TOKEN"]
with open(path, "w", encoding="utf-8") as config:
    json.dump({"site": site, "token": token}, config)
    config.write("\n")
os.chmod(path, 0o600)
PY
unset BIO_TOKEN
install -m 755 "$SCRIPT_DIR/steam-presence-bridge.py" "$HOME/.local/bin/steam-presence-bridge"
install -m 644 "$SCRIPT_DIR/personal-bio-steam-bridge.service" "$HOME/.config/systemd/user/personal-bio-steam-bridge.service"
systemctl --user daemon-reload
systemctl --user enable personal-bio-steam-bridge.service
systemctl --user restart personal-bio-steam-bridge.service
echo "Steam and Spotify bridge installed and started. It will start automatically when you sign in."
if ! command -v playerctl >/dev/null 2>&1; then
  echo "Spotify presence needs playerctl. Install it on Bazzite, then restart the service."
fi
echo "To check it later: systemctl --user status personal-bio-steam-bridge"
