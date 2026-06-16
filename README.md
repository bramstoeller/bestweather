# BestWeather

Find the **best** (warmest & driest) forecast for any place by querying every
free weather API at once. A websocket streams results live: each source the
server queries pushes an update, and the forecast improves as better weather is
found — until all sources are done.

- **Mobile-first**, dead-simple UI, light/dark mode.
- **Current location** via the browser Geolocation API, or **search** any place.
- **Favorites** saved locally in the browser (no account, no database).
- **Today + 15 days** of "best of all sources" forecast.
- **Multilingual** (auto-detected): English + Dutch.
- Server-side **caching** of every provider's result.

## Weather sources

Keyless (work out of the box):

- **Open-Meteo** — worldwide, up to 16 days.
- **MET Norway (yr.no)** — worldwide.
- **Bright Sky (DWD)** — best around Germany.

Optional (enabled automatically when you add a free API key to `.env`):

- **OpenWeatherMap** (`OPENWEATHERMAP_API_KEY`)
- **WeatherAPI.com** (`WEATHERAPI_API_KEY`)

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: add API keys
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## How "best" is defined

Per day we compute `score = temp_max − 1.5·precip_mm − 0.05·rain_chance%` and keep
the highest-scoring day across all providers. See `app/scoring.py`.

## Layout

```
app/
  main.py          FastAPI app: static, /api/search, /api/reverse, /ws
  forecast.py      Concurrent provider fan-out + live streaming
  scoring.py       What "best weather" means
  providers/       One file per weather source (normalized to DayForecast)
  geocoding.py     Forward + reverse geocoding (keyless)
  cache.py         Async TTL cache
static/            Mobile-first frontend (vanilla JS, no build step)
```
