# Deploying BestWeather to mooisteweer.nl

> ⚠️ **Live, shared Apache server** (`vps1541`, Ubuntu 18.04) hosting ~20 other
> vhosts. Everything below is additive and scoped to BestWeather only: a service
> bound to **127.0.0.1:8800** and one new Apache vhost for `mooisteweer.nl`.
> No existing site, module behaviour, or port binding of other apps is changed.

## What runs where

- **App**: `~/bestweather` (no root needed), Python 3.8 venv, uvicorn on
  `127.0.0.1:8800`.
- **Public**: Apache reverse-proxies `mooisteweer.nl` → `127.0.0.1:8800`,
  tunnelling the `/ws` websocket via `mod_proxy_wstunnel`.

## 1. Deploy the code (no sudo)

From your laptop:

```bash
rsync -az --delete \
  --exclude .venv --exclude .git --exclude __pycache__ --exclude .env \
  ./ user@your-server:~/bestweather/
```

On the server:

```bash
cd ~/bestweather
python3.8 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r deploy/requirements-py38.txt
cp .env.example .env        # optional: add OPENWEATHERMAP_API_KEY / WEATHERAPI_API_KEY
# Smoke test (Ctrl-C after the health check):
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8800 &
sleep 2 && curl -s http://127.0.0.1:8800/api/health && kill %1
```

## 2. Privileged setup (needs sudo)

Modules + service + vhost, all in one guarded script that aborts on any Apache
config error and reloads (never restarts) Apache:

```bash
sudo bash ~/bestweather/deploy/server-setup-root.sh
```

This: enables `proxy proxy_http proxy_wstunnel`, installs+starts the
`bestweather` systemd service, installs the vhost, runs `apache2ctl configtest`,
then `systemctl reload apache2`.

## 3. HTTPS (after DNS points here)

Geolocation needs HTTPS. Once `mooisteweer.nl` resolves to `your-server`:

```bash
sudo apt-get install -y certbot python3-certbot-apache
sudo certbot --apache -d mooisteweer.nl -d www.mooisteweer.nl
```

## Update later

```bash
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .env \
  ./ user@your-server:~/bestweather/
ssh user@your-server 'cd ~/bestweather && .venv/bin/pip install -r deploy/requirements-py38.txt && sudo systemctl restart bestweather'
```

## Rollback (clean removal)

```bash
sudo a2dissite mooisteweer_nl && sudo systemctl reload apache2
sudo systemctl disable --now bestweather
sudo rm /etc/systemd/system/bestweather.service && sudo systemctl daemon-reload
sudo rm /etc/apache2/sites-available/mooisteweer_nl.conf
# (proxy modules can stay enabled; harmless. ~/bestweather can be deleted.)
```
