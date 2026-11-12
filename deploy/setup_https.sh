#!/usr/bin/env bash
# Включает HTTPS: nginx + бесплатный сертификат Let's Encrypt для вашего домена.
# Перед запуском: A-запись домена должна указывать на IP этого сервера.
# Запуск от root:  bash /opt/dispatcher/deploy/setup_https.sh example.ru [email]
# Другие сайты nginx на этом сервере не затрагиваются.
set -euo pipefail
DOMAIN="${1:?укажите домен, например: setup_https.sh dispatcher.example.ru}"
EMAIL="${2:-}"
APP_DIR=/opt/dispatcher
PORT=8000

MY_IP="$(curl -fsS -4 https://api.ipify.org || true)"
DNS_IP="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}')"
if [ -z "$DNS_IP" ] || { [ -n "$MY_IP" ] && [ "$DNS_IP" != "$MY_IP" ]; }; then
  echo "Домен $DOMAIN указывает на '${DNS_IP:-ничего}', а IP сервера — $MY_IP." >&2
  echo "Сначала настройте A-запись домена на $MY_IP и подождите 5–30 минут." >&2
  exit 1
fi
if ! command -v nginx >/dev/null && ss -ltn '( sport = :80 )' | grep -q LISTEN; then
  echo "Порт 80 уже занят другой программой (не nginx). Остановлено, ничего не изменено:" >&2
  ss -ltnp '( sport = :80 )' >&2
  exit 1
fi

apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx >/dev/null

cat > /etc/nginx/sites-available/dispatcher <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    client_max_body_size 2m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/dispatcher /etc/nginx/sites-enabled/dispatcher
nginx -t
systemctl enable --now nginx
systemctl reload nginx

if ufw status 2>/dev/null | grep -q "Status: active"; then ufw allow 'Nginx Full' >/dev/null; fi

if [ -n "$EMAIL" ]; then MAIL_ARGS=(-m "$EMAIL"); else MAIL_ARGS=(--register-unsafely-without-email); fi
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect "${MAIL_ARGS[@]}"

# Приложение слушает только локально: снаружи доступ теперь лишь через HTTPS.
touch "$APP_DIR/.env" && chown dispatcher:dispatcher "$APP_DIR/.env" && chmod 600 "$APP_DIR/.env"
grep -v -E '^(HOST|FORWARDED_ALLOW_IPS)=' "$APP_DIR/.env" > "$APP_DIR/.env.tmp" || true
printf 'HOST=127.0.0.1\nFORWARDED_ALLOW_IPS=127.0.0.1\n' >> "$APP_DIR/.env.tmp"
mv "$APP_DIR/.env.tmp" "$APP_DIR/.env" && chown dispatcher:dispatcher "$APP_DIR/.env" && chmod 600 "$APP_DIR/.env"
systemctl restart dispatcher
sleep 3
curl -fsS "https://$DOMAIN/" && echo && echo "=== Готово: https://$DOMAIN/ui/  (сертификат продлевается автоматически)"
