# Deploying MooisteWeer

The app is a git checkout on the server. The nginx vhost and the systemd unit
are **symlinks into this checkout**, so a deploy is just `git pull` + restart.

The host runs nginx with Python 3.14, passwordless sudo and SELinux. The app
lives in `/var/www/<domain>` and runs as a systemd service on `127.0.0.1:8800`.

```bash
HOST=user@your-server
APPDIR=/var/www/mooisteweer.nl
REPO=https://github.com/<owner>/<repo>.git
```

## First-time setup

```bash
ssh "$HOST" "bash -lc '
  cd $APPDIR
  git init -q && git remote add origin $REPO
  git fetch -q origin && git checkout -f -b main origin/main
  python3 -m venv .venv && .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/pip install -q -r deploy/requirements-server.txt
  [ -f .env ] || install -m 600 .env.example .env   # add API keys + CONTACT_EMAIL
  mkdir -p ssl certbot
'"
```

`.env`, `.venv`, `ssl/` and `certbot/` are gitignored, so `git pull` never
touches them.

SELinux: the venv must be executable by systemd, the app port must be an http
port, and the symlinked unit file needs the unit label:

```bash
ssh "$HOST" "bash -lc '
  sudo semanage fcontext -a -t bin_t \"$APPDIR/.venv/bin(/.*)?\" && sudo restorecon -RvF $APPDIR/.venv/bin
  sudo semanage port -a -t http_port_t -p tcp 8800 || true
  # The symlinked unit target must carry the unit label (restorecon needs -F).
  sudo semanage fcontext -a -t systemd_unit_file_t \"$APPDIR/deploy/bestweather.service\" && sudo restorecon -vF $APPDIR/deploy/bestweather.service
'"
```

## Symlinks (service + vhost)

The repo's unit uses a generic `User=deploy`. Keep your real deploy user out of
the repo with a server-local drop-in:

```bash
DEPLOY_USER=youruser   # the account the service runs as
ssh "$HOST" "bash -lc '
  sudo ln -sfn $APPDIR/deploy/bestweather.service /etc/systemd/system/bestweather.service
  sudo mkdir -p /etc/systemd/system/bestweather.service.d
  printf \"[Service]\nUser=$DEPLOY_USER\nGroup=$DEPLOY_USER\n\" | sudo tee /etc/systemd/system/bestweather.service.d/override.conf
  sudo systemctl daemon-reload && sudo systemctl enable --now bestweather

  sudo ln -sfn $APPDIR/deploy/nginx-https.conf /etc/nginx/conf.d/mooisteweer.nl.conf
  cat $APPDIR/ssl/certificate.crt $APPDIR/ssl/cabundle.crt > $APPDIR/ssl/fullchain.crt
  sudo nginx -t && sudo systemctl reload nginx
'"
```

(Before the TLS certs land, point the conf.d symlink at `deploy/nginx.conf` for
an HTTP-only stage so `nginx -t` cannot fail on a missing cert.)

## Deploy an update

```bash
ssh "$HOST" "$APPDIR/deploy/update.sh"
```

`update.sh` pulls, installs deps and restarts the service. The vhost and unit
are symlinks, so changes to them land on `git pull`; reload nginx
(`sudo nginx -t && sudo systemctl reload nginx`) when the vhost changed, and
`sudo systemctl daemon-reload` when the unit changed.
