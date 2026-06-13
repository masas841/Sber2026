#!/usr/bin/env bash
# Установка photo_receiver на Linux VPS (Greathearted Inna)
set -eu

APP_DIR="${1:-/opt/photo-receiver}"
PORT="${PORT:-8767}"
PUBLIC_URL="${PUBLIC_URL:-https://sberfest2026.ru}"

echo "=== photo_receiver install -> $APP_DIR ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip curl

cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
fi
sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=$PUBLIC_URL|" .env
sed -i "s|^PORT=.*|PORT=$PORT|" .env

mkdir -p data/uploads data/parts

cat >/etc/systemd/system/photo-receiver.service <<EOF
[Unit]
Description=GIGAvibe Photo Receiver
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable photo-receiver
systemctl restart photo-receiver

if command -v ufw >/dev/null 2>&1; then
  ufw allow "${PORT}/tcp" || true
fi

sleep 2
curl -sf "http://127.0.0.1:${PORT}/api/health" && echo
echo "OK: photo-receiver on :${PORT}"
