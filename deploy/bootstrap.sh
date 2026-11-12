#!/usr/bin/env bash
# Разовая подготовка сервера (Ubuntu/Debian). Запуск от root:
#   curl -fsSL https://raw.githubusercontent.com/valeriiv86-commits/dispatcher/main/deploy/bootstrap.sh | bash
# Затем добавьте выведенный в конце приватный ключ в GitHub-секрет SSH_KEY.
set -euo pipefail
APP_DIR=/opt/dispatcher
apt-get update -qq && apt-get install -y -qq git python3-venv curl >/dev/null
id dispatcher &>/dev/null || useradd -r -m -s /bin/bash dispatcher
[ -d "$APP_DIR/.git" ] || git clone -q https://github.com/valeriiv86-commits/dispatcher.git "$APP_DIR"
chown -R dispatcher:dispatcher "$APP_DIR"
sudo -u dispatcher python3 -m venv "$APP_DIR/venv"
sudo -u dispatcher "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
cp "$APP_DIR/deploy/dispatcher.service" /etc/systemd/system/
echo "dispatcher ALL=(root) NOPASSWD: /usr/bin/systemctl restart dispatcher, /bin/systemctl restart dispatcher" > /etc/sudoers.d/dispatcher
chmod 440 /etc/sudoers.d/dispatcher
systemctl daemon-reload && systemctl enable --now dispatcher
# Ключ для GitHub Actions
KEY=/home/dispatcher/.ssh/github_deploy
if [ ! -f "$KEY" ]; then
  sudo -u dispatcher mkdir -p -m 700 /home/dispatcher/.ssh
  sudo -u dispatcher ssh-keygen -q -t ed25519 -N "" -C github-deploy -f "$KEY"
  cat "$KEY.pub" >> /home/dispatcher/.ssh/authorized_keys
  chown dispatcher:dispatcher /home/dispatcher/.ssh/authorized_keys && chmod 600 /home/dispatcher/.ssh/authorized_keys
fi
sleep 2; curl -fsS http://127.0.0.1:8000/ && echo
echo "=== Готово. В GitHub → Settings → Secrets → Actions добавьте:"
echo "SSH_HOST = $(curl -fsS https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
echo "SSH_USER = dispatcher"
echo "SSH_KEY  = (всё содержимое ниже, включая строки BEGIN/END)"
cat "$KEY"
