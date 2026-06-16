#!/usr/bin/env bash
# Pull the latest code and restart the service. Run on the server, from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --ff-only
.venv/bin/pip install -q -r deploy/requirements-server.txt
sudo systemctl restart bestweather
sleep 2
curl -fsS http://127.0.0.1:8800/api/health >/dev/null && echo "bestweather restarted and healthy"
