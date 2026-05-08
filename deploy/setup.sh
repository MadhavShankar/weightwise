#!/bin/bash
# Run this once on the VPS as root to set up the API server.
set -e

PROJECT_DIR=/opt/weightwise
SERVICE_USER=weightwise

echo "=== 1. Create service user ==="
id "$SERVICE_USER" &>/dev/null || useradd -r -s /bin/false "$SERVICE_USER"

echo "=== 2. Clone / copy project ==="
# If deploying from local machine, rsync instead:
#   rsync -av --exclude node_modules --exclude .git . root@VPS_IP:/opt/weightwise/
mkdir -p "$PROJECT_DIR"
chown "$SERVICE_USER":"$SERVICE_USER" "$PROJECT_DIR"

echo "=== 3. Python venv ==="
cd "$PROJECT_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r web_api/requirements.txt
# Also install bot dependencies (shared services/ imports)
venv/bin/pip install -r requirements.txt

echo "=== 4. Copy .env ==="
# Copy your .env file to /opt/weightwise/.env manually, then:
chown "$SERVICE_USER":"$SERVICE_USER" .env
chmod 600 .env

echo "=== 5. Install systemd service ==="
cp deploy/weightwise-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable weightwise-api
systemctl start weightwise-api

echo "=== 6. Install nginx config ==="
cp deploy/nginx-api.weightwise.in.conf /etc/nginx/sites-available/api.weightwise.in
ln -sf /etc/nginx/sites-available/api.weightwise.in /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "=== 7. SSL cert (certbot) ==="
certbot --nginx -d api.weightwise.in --non-interactive --agree-tos -m madshankarkel@gmail.com

echo ""
echo "Done. Test: curl https://api.weightwise.in/health"
