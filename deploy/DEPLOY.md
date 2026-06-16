# Deploying BestWeather to mooisteweer.nl

Target: `user@your-server` (Fedora 43, nginx, Python 3.14, passwordless
sudo). Follows the house style of `ehbo.app` on the same host: code in
`/var/www/<domain>`, the vhost lives in the repo and is symlinked into
`/etc/nginx/conf.d/`, the app runs as a systemd service on `127.0.0.1:8800`.

> Shared host — other vhosts (ehbo.app) run here. Every step is additive and the
> nginx change is staged so `nginx -t` can never fail on a missing TLS cert.

## 1. Code + venv (`/var/www/mooisteweer.nl`)

```bash
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .env \
  ./ user@your-server:/var/www/mooisteweer.nl/
ssh user@your-server 'bash -lc "
  cd /var/www/mooisteweer.nl
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/pip install -r deploy/requirements-server.txt
  [ -f .env ] || install -m 600 .env.example .env   # add API keys here (kept out of git)
  mkdir -p certbot ssl
"'
```

## 2. systemd service (localhost:8800)

```bash
ssh user@your-server 'bash -lc "
  sudo cp /var/www/mooisteweer.nl/deploy/bestweather.service /etc/systemd/system/bestweather.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now bestweather
  sleep 2 && curl -fsS http://127.0.0.1:8800/api/health
"'
```

## 3. nginx vhost — HTTP stage (safe before certs)

```bash
ssh user@your-server 'bash -lc "
  sudo ln -sfn /var/www/mooisteweer.nl/deploy/nginx.conf /etc/nginx/conf.d/mooisteweer.nl.conf
  sudo nginx -t && sudo systemctl reload nginx
  curl -fsS http://mooisteweer.nl/api/health
"'
```

The site is now live over HTTP at http://mooisteweer.nl.

## 4. HTTPS stage (after the cert files land in `ssl/`)

Drop `certificate.crt`, `certificate.key`, `cabundle.crt` into
`/var/www/mooisteweer.nl/ssl/`, then switch the vhost to the HTTPS version:

```bash
ssh user@your-server 'bash -lc "
  cp /var/www/mooisteweer.nl/deploy/nginx-https.conf /var/www/mooisteweer.nl/deploy/nginx.conf
  sudo nginx -t && sudo systemctl reload nginx
"'
```

(`nginx.conf` is the symlinked file; overwriting it with the HTTPS variant and
reloading is the whole switch. `git checkout deploy/nginx.conf` to undo locally.)

Geolocation ("use my location") only works over HTTPS, so finish this step
before relying on it.

## Update later

```bash
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .env \
  ./ user@your-server:/var/www/mooisteweer.nl/
ssh user@your-server 'cd /var/www/mooisteweer.nl && .venv/bin/pip install -r deploy/requirements-server.txt && sudo systemctl restart bestweather'
```

## Rollback (clean)

```bash
ssh user@your-server 'bash -lc "
  sudo rm -f /etc/nginx/conf.d/mooisteweer.nl.conf && sudo nginx -t && sudo systemctl reload nginx
  sudo systemctl disable --now bestweather
  sudo rm -f /etc/systemd/system/bestweather.service && sudo systemctl daemon-reload
  rm -rf /var/www/mooisteweer.nl
"'
```
