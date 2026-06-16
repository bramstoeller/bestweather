"""Live, progressive best-weather search across providers."""

import asyncio
from datetime import date as date_cls
from datetime import timedelta
from typing import Awaitable, Callable, Dict, List

import httpx

from .cache import cache
from .config import settings
from .models import DayForecast
from .providers import Provider, active_providers
from .scoring import Profile, merge_best

Emit = Callable[[dict], Awaitable[None]]


def _web_link(source: dict, lat: float, lon: float) -> str:
    """Best public page for a source at this place (falls back to its homepage)."""
    url = source["url"]
    la, lo = f"{lat:.4f}", f"{lon:.4f}"
    if "open-meteo.com" in url:
        link = (
            f"https://open-meteo.com/en/docs?latitude={la}&longitude={lo}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        )
        model = source.get("model")
        return f"{link}&models={model}" if model else link
    if "yr.no" in url:
        return f"https://www.yr.no/en/forecast/daily-table/{la},{lo}"
    if "wttr.in" in url:
        return f"https://wttr.in/{la},{lo}"
    if "openweathermap.org" in url:
        return f"https://openweathermap.org/weathermap?lat={la}&lon={lo}&zoom=10"
    if "visualcrossing.com" in url:
        return f"https://www.visualcrossing.com/weather/weather-data-services/{la},{lo}"
    return url


async def _cached_fetch(provider: Provider, client, lat, lon) -> dict:
    key = f"fc:{provider.name}:{round(lat, 2)}:{round(lon, 2)}"
    cached = await cache.get(key)
    if cached is not None:
        return cached
    result = await provider.fetch_sources(client, lat, lon)
    await cache.set(key, result, settings.cache_ttl_seconds)
    return result


def _window(best: Dict[str, DayForecast], hourly_by_date: Dict[str, list]) -> List[dict]:
    today = date_cls.today().isoformat()
    last = (date_cls.today() + timedelta(days=settings.forecast_days - 1)).isoformat()
    chosen = [best[d] for d in sorted(best) if today <= d <= last][: settings.forecast_days]
    out = []
    for day in chosen:
        d = day.to_dict()
        if not d.get("hourly"):
            d["hourly"] = hourly_by_date.get(day.date)
        out.append(d)
    return out


async def run_best_weather(lat: float, lon: float, profile: Profile, emit: Emit) -> None:
    """Query every active provider concurrently, streaming the best so far.

    Provider forecasts are scored with the given profile; the best day per date
    wins. Hourly detail comes from whichever provider supplies it (Open-Meteo)
    and is attached to every day regardless of which source won the score.
    """
    providers = active_providers()
    sources = []
    for p in providers:
        sources.extend(p.sources())
    for s in sources:
        s["link"] = _web_link(s, lat, lon)
    total = len(sources)
    await emit({"type": "providers", "sources": sources, "total": total})

    best: Dict[str, DayForecast] = {}
    hourly_by_date: Dict[str, list] = {}

    async def handle(provider: Provider, client):
        try:
            return provider, await _cached_fetch(provider, client, lat, lon), None
        except Exception as exc:  # noqa: BLE001 - surface any provider failure
            return provider, {}, str(exc)

    async with httpx.AsyncClient(timeout=settings.http_timeout, follow_redirects=True) as client:
        tasks = [asyncio.create_task(handle(p, client)) for p in providers]
        done = 0
        for coro in asyncio.as_completed(tasks):
            provider, result_map, error = await coro
            names = [s["name"] for s in provider.sources()]
            done += len(names)
            changed = False
            statuses = {}
            for name in names:
                days = result_map.get(name)
                if days:
                    for d in days:
                        if d.hourly and d.date not in hourly_by_date:
                            hourly_by_date[d.date] = d.hourly
                    if merge_best(best, days, name, profile):
                        changed = True
                    statuses[name] = "ok"
                else:
                    statuses[name] = "error"
            await emit(
                {
                    "type": "update",
                    "statuses": statuses,
                    "error": error,
                    "done": done,
                    "total": total,
                    "changed": changed,
                    "days": _window(best, hourly_by_date),
                }
            )

    await emit({"type": "complete", "total": total, "days": _window(best, hourly_by_date)})
