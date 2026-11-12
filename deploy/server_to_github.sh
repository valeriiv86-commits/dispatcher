#!/usr/bin/env bash
# Разовая копия кода С СЕРВЕРА в GitHub (если на сервере есть то, чего нет в репо).
# Запуск на сервере: bash server_to_github.sh /путь/к/коду/на/сервере
# Секреты (.env, ключи) не копируются — см. .gitignore.
set -euo pipefail
SRC="${1:?укажите папку с кодом на сервере}"
REPO="https://github.com/valeriiv86-commits/dispatcher.git"
TMP="$(mktemp -d)"
git clone --quiet "$REPO" "$TMP"
cd "$TMP"
git checkout -b server-snapshot-$(date +%Y%m%d-%H%M)
rsync -a --delete --exclude .git --exclude venv --exclude .env --exclude __pycache__ "$SRC"/ ./
git add -A
git commit -m "Snapshot of production server code" && git push -u origin HEAD
echo "Готово: откройте PR из ветки $(git branch --show-current) в main и сравните."
