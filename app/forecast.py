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


async def _cached_fetch(provider: Provider, client, lat, lon) -> List[DayForecast]:
    key = f"fc:{provider.name}:{round(lat, 2)}:{round(lon, 2)}"
    cached = await cache.get(key)
    if cached is not None:
        return cached
    days = await provider.fetch(client, lat, lon)
    await cache.set(key, days, settings.cache_ttl_seconds)
    return days


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
    await emit(
        {
            "type": "providers",
            "sources": [
                {"name": p.name, "url": p.url, "keyless": not p.requires_key, "region": p.region}
                for p in providers
            ],
            "total": len(providers),
        }
    )

    best: Dict[str, DayForecast] = {}
    hourly_by_date: Dict[str, list] = {}

    async def handle(provider: Provider, client):
        try:
            return provider, await _cached_fetch(provider, client, lat, lon), "ok", None
        except Exception as exc:  # noqa: BLE001 - surface any provider failure
            return provider, [], "error", str(exc)

    async with httpx.AsyncClient(timeout=settings.http_timeout, follow_redirects=True) as client:
        tasks = [asyncio.create_task(handle(p, client)) for p in providers]
        done = 0
        for coro in asyncio.as_completed(tasks):
            provider, days, status, error = await coro
            done += 1
            changed = False
            if status == "ok":
                for d in days:
                    if d.hourly and d.date not in hourly_by_date:
                        hourly_by_date[d.date] = d.hourly
                changed = merge_best(best, days, provider.name, profile)
            await emit(
                {
                    "type": "update",
                    "provider": provider.name,
                    "status": status,
                    "error": error,
                    "done": done,
                    "total": len(providers),
                    "changed": changed,
                    "days": _window(best, hourly_by_date),
                }
            )

    await emit({"type": "complete", "total": len(providers), "days": _window(best, hourly_by_date)})
