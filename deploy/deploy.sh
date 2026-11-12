#!/usr/bin/env bash
# Запускается на сервере (из GitHub Actions или вручную): подтянуть main и перезапустить.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
if [ -z "${DEPLOY_REEXEC:-}" ]; then
  git fetch --quiet origin main
  git reset --hard --quiet origin/main
  # Перезапускаем себя, чтобы выполнялась уже новая версия этого скрипта.
  DEPLOY_REEXEC=1 exec bash "$APP_DIR/deploy/deploy.sh"
fi
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q -r requirements.txt
# Резервная копия базы перед перезапуском (храним 14 последних).
DB="${DB_PATH:-$APP_DIR/data/dispatcher.db}"
if [ -f "$DB" ]; then
  mkdir -p "$APP_DIR/data/backups"
  venv/bin/python - "$DB" "$APP_DIR/data/backups/dispatcher-$(date +%Y%m%d-%H%M%S).db" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
  ls -1t "$APP_DIR"/data/backups/*.db | tail -n +15 | xargs -r rm -f
fi
sudo systemctl restart dispatcher
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "http://127.0.0.1:${PORT:-8000}/" >/dev/null 2>&1; then
    echo "deploy OK: $(git rev-parse --short HEAD)"; exit 0
  fi
  sleep 1
done
echo "deploy FAILED: сервис не отвечает на порту ${PORT:-8000}" >&2
exit 1
