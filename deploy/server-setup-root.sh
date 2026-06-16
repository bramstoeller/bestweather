#!/usr/bin/env bash
# Privileged setup for BestWeather on the mooisteweer.nl server.
# Run AFTER the app is deployed and verified on http://127.0.0.1:8800.
#
#   sudo bash deploy/server-setup-root.sh
#
# Every step is additive and scoped to BestWeather. It does NOT modify any
# existing vhost. It aborts immediately if Apache config validation fails.
set -euo pipefail

REPO="/home/deploy/bestweather"

echo "==> 1/4 Enabling Apache proxy modules (no effect on existing sites)"
a2enmod proxy proxy_http proxy_wstunnel

echo "==> 2/4 Installing the systemd service (localhost:8800 only)"
cp "$REPO/deploy/bestweather.service" /etc/systemd/system/bestweather.service
systemctl daemon-reload
systemctl enable --now bestweather
sleep 2
curl -fsS http://127.0.0.1:8800/api/health && echo " <- service healthy"

echo "==> 3/4 Installing the mooisteweer.nl vhost"
cp "$REPO/deploy/apache-mooisteweer.conf" /etc/apache2/sites-available/mooisteweer_nl.conf
a2ensite mooisteweer_nl

echo "==> 4/4 Validating Apache config BEFORE reload"
apache2ctl configtest        # aborts the script on any error (set -e)
systemctl reload apache2     # reload, not restart -> no downtime for other sites

echo
echo "DONE. BestWeather is live over HTTP once DNS points mooisteweer.nl here."
echo "For HTTPS (needed for geolocation), after DNS propagates run:"
echo "  sudo apt-get install -y certbot python3-certbot-apache"
echo "  sudo certbot --apache -d mooisteweer.nl -d www.mooisteweer.nl"
