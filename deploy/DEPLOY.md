# Deploying MooisteWeer

The host runs nginx with Python 3.14 and passwordless sudo. The app lives in
`/var/www/<domain>`, its vhost lives in this repo and is symlinked into
`/etc/nginx/conf.d/`, and it runs as a systemd service on `127.0.0.1:8800`.

Set your own target first; nothing about the server is hard-coded in the repo:

```bash
HOST=user@your-server           # ssh target
APPDIR=/var/www/mooisteweer.nl  # app directory on the server
```

> Shared host: other vhosts may run here. Every step is additive and the nginx
> change is staged so `nginx -t` can never fail on a missing TLS cert.

## 1. Code + venv

```bash
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .env --exclude ssl \
  ./ "$HOST:$APPDIR/"
ssh "$HOST" "bash -lc '
  cd $APPDIR
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/pip install -r deploy/requirements-server.txt
  [ -f .env ] || install -m 600 .env.example .env   # add API keys + CONTACT_EMAIL here
  mkdir -p certbot ssl
'"
```

On SELinux hosts the venv binaries must be executable by systemd, and the app
port must be labelled as an http port:

```bash
ssh "$HOST" 'sudo semanage fcontext -a -t bin_t "'"$APPDIR"'/.venv/bin(/.*)?" && sudo restorecon -RvF '"$APPDIR"'/.venv/bin'
ssh "$HOST" 'sudo semanage port -a -t http_port_t -p tcp 8800 || true'
```

## 2. systemd service (localhost:8800)

```bash
ssh "$HOST" "bash -lc '
  sudo cp $APPDIR/deploy/bestweather.service /etc/systemd/system/bestweather.service
  sudo systemctl daemon-reload && sudo systemctl enable --now bestweather
  sleep 2 && curl -fsS http://127.0.0.1:8800/api/health
'"
```

## 3. nginx vhost

HTTP first (safe before certs), then HTTPS once the cert files are in `ssl/`
(`certificate.crt`, `certificate.key`, `cabundle.crt`):

```bash
# HTTP stage
ssh "$HOST" "sudo ln -sfn $APPDIR/deploy/nginx.conf /etc/nginx/conf.d/mooisteweer.nl.conf && sudo nginx -t && sudo systemctl reload nginx"

# HTTPS stage: build the full chain, then switch the vhost
ssh "$HOST" "bash -lc '
  cat $APPDIR/ssl/certificate.crt $APPDIR/ssl/cabundle.crt > $APPDIR/ssl/fullchain.crt
  sudo ln -sfn $APPDIR/deploy/nginx-https.conf /etc/nginx/conf.d/mooisteweer.nl.conf
  sudo nginx -t && sudo systemctl reload nginx
'"
```

## Update later

```bash
rsync -az --exclude .venv --exclude .git --exclude __pycache__ --exclude .env --exclude ssl \
  ./ "$HOST:$APPDIR/"
ssh "$HOST" "cd $APPDIR && .venv/bin/pip install -r deploy/requirements-server.txt && sudo systemctl restart bestweather"
```
