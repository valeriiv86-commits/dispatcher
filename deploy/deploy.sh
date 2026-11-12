#!/usr/bin/env bash
# Запускается на сервере (из GitHub Actions или вручную): подтянуть main и перезапустить.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
git fetch --quiet origin main
git reset --hard origin/main
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q -r requirements.txt
sudo systemctl restart dispatcher
sleep 2
curl -fsS "http://127.0.0.1:${PORT:-8000}/" >/dev/null && echo "deploy OK: $(git rev-parse --short HEAD)"
