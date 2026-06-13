#!/usr/bin/env bash
# nginx + Let's Encrypt для sberfest2026.ru → photo_receiver (127.0.0.1:8767)
set -eu

DOMAIN="${DOMAIN:-sberfest2026.ru}"
EMAIL="${EMAIL:-admin@sberfest2026.ru}"
APP_DIR="${APP_DIR:-/opt/photo-receiver}"
PUBLIC_URL="https://${DOMAIN}"

echo "=== SSL setup: $DOMAIN ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx curl

# photo_receiver только на localhost
if [[ -f "$APP_DIR/.env" ]]; then
  sed -i 's|^HOST=.*|HOST=127.0.0.1|' "$APP_DIR/.env"
  sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=$PUBLIC_URL|" "$APP_DIR/.env"
  sed -i 's|^PORT=.*|PORT=8767|' "$APP_DIR/.env"
fi
systemctl restart photo-receiver

cat >/etc/nginx/sites-available/photo-receiver <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    client_max_body_size 32m;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml image/svg+xml;

    location /static/css/ {
        proxy_pass http://127.0.0.1:8767;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Cache-Control "public, max-age=300" always;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8767;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
    }

    location /outputs/ {
        proxy_pass http://127.0.0.1:8767;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Cache-Control "public, max-age=604800, immutable" always;
    }

    location / {
        proxy_pass http://127.0.0.1:8767;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_request_buffering off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/photo-receiver /etc/nginx/sites-enabled/photo-receiver
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl reload nginx

if ufw status 2>/dev/null | grep -q inactive; then
  ufw allow OpenSSH || true
  ufw allow 'Nginx Full' || ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ufw --force enable || true
else
  ufw allow 'Nginx Full' || true
fi

RESOLVED_IP="$(dig +short "$DOMAIN" @8.8.8.8 | head -1)"
SERVER_IP="$(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
if [[ "$RESOLVED_IP" == "$SERVER_IP" ]] || [[ "$RESOLVED_IP" == "45.67.59.125" ]]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
  systemctl reload nginx
  sleep 2
  curl -sf "https://${DOMAIN}/api/health"
  echo
  echo "OK: https://${DOMAIN}"
else
  echo "WARN: DNS для $DOMAIN не указывает на этот сервер (A=$RESOLVED_IP, server=$SERVER_IP)."
  echo "Добавьте A-запись в панели Beget, затем: certbot --nginx -d $DOMAIN --redirect"
fi
