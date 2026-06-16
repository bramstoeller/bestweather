# Deploying BestWeather to mooisteweer.nl

> ⚠️ **This is a live, shared server.** Every step below is additive and scoped
> to BestWeather only — a localhost-bound service on port **8800** and a single
> new nginx vhost for `mooisteweer.nl`. Nothing here touches other apps, the
> default vhost, or ports 80/443 bindings of other services. Read before running.

## 0. Pre-flight (read-only — safe to run)

Confirm what's already there so we don't collide:

```bash
# Which reverse proxy is in front? (expect nginx; if apache/caddy, adapt)
sudo nginx -v 2>&1 || true
# Is our chosen port free? (expect NO output)
sudo ss -ltnp | grep ':8800' || echo "8800 is free"
# Does an upgrade map already exist? (if yes, drop the map block from our conf)
sudo grep -Rn "connection_upgrade" /etc/nginx/ || echo "no existing upgrade map"
# Is the DNS for the domain pointing here yet?
dig +short mooisteweer.nl
```

## 1. Get the code onto the server

```bash
sudo mkdir -p /opt/bestweather
sudo chown "$USER" /opt/bestweather
git clone <this-repo-url> /opt/bestweather   # or rsync the directory
cd /opt/bestweather
```

## 2. Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # add OPENWEATHERMAP_API_KEY / WEATHERAPI_API_KEY if you have them
```

## 3. Run as a service (localhost only)

```bash
sudo cp deploy/bestweather.service /etc/systemd/system/bestweather.service
# Edit User/Group/paths in the unit if your setup differs.
sudo chown -R www-data:www-data /opt/bestweather
sudo systemctl daemon-reload
sudo systemctl enable --now bestweather
sudo systemctl status bestweather --no-pager
curl -s http://127.0.0.1:8800/api/health    # expect {"status":"ok",...}
```

At this point the app runs but is NOT yet public — good for a safe smoke test.

## 4. Expose via nginx (one new vhost, scoped to the domain)

```bash
sudo cp deploy/nginx-mooisteweer.conf /etc/nginx/sites-available/mooisteweer.nl
sudo ln -s /etc/nginx/sites-available/mooisteweer.nl /etc/nginx/sites-enabled/
# If pre-flight found an existing connection_upgrade map, delete the map{} block
# from the copied file first to avoid a duplicate.
sudo nginx -t                 # MUST pass before reloading
sudo systemctl reload nginx   # reload (not restart) — no downtime for other sites
```

Visit http://mooisteweer.nl — you should see BestWeather.

## 5. HTTPS (geolocation needs it)

The browser Geolocation API only works on HTTPS (or localhost). Add a cert for
just this domain — certbot edits only our vhost:

```bash
sudo certbot --nginx -d mooisteweer.nl -d www.mooisteweer.nl
```

## Updating later

```bash
cd /opt/bestweather && git pull && .venv/bin/pip install -r requirements.txt
sudo systemctl restart bestweather
```

## Rollback / removal (clean, no leftovers)

```bash
sudo rm /etc/nginx/sites-enabled/mooisteweer.nl && sudo nginx -t && sudo systemctl reload nginx
sudo systemctl disable --now bestweather
sudo rm /etc/systemd/system/bestweather.service && sudo systemctl daemon-reload
```
