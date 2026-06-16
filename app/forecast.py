"""Orchestrates the live, progressive best-weather search across providers."""

import asyncio
from datetime import date as date_cls
from datetime import timedelta
from typing import Awaitable, Callable, Dict, List

import httpx

from .cache import cache
from .config import settings
from .models import DayForecast
from .providers import Provider, active_providers
from .scoring import merge_best

# An async callback the websocket layer passes in to push messages to the client.
Emit = Callable[[dict], Awaitable[None]]


async def _cached_fetch(
    provider: Provider, client: httpx.AsyncClient, lat: float, lon: float
) -> List[DayForecast]:
    key = f"fc:{provider.name}:{round(lat, 2)}:{round(lon, 2)}"
    cached = await cache.get(key)
    if cached is not None:
        return cached
    days = await provider.fetch(client, lat, lon)
    await cache.set(key, days, settings.cache_ttl_seconds)
    return days


def _window(best: Dict[str, DayForecast]) -> List[dict]:
    """Return the best forecast for today .. today+N, sorted, as dicts."""
    today = date_cls.today().isoformat()
    last = (date_cls.today() + timedelta(days=settings.forecast_days - 1)).isoformat()
    days = [best[d] for d in sorted(best) if today <= d <= last]
    return [d.to_dict() for d in days[: settings.forecast_days]]


async def run_best_weather(lat: float, lon: float, emit: Emit) -> None:
    """Query every active provider concurrently and stream improving results.

    Emits, in order:
      - {type: "providers", ...}        once, listing the sources being queried
      - {type: "update", ...}           per provider as it finishes (ok or error)
      - {type: "complete", ...}         once, when all providers are done
    """
    providers = active_providers()
    await emit(
        {
            "type": "providers",
            "providers": [p.name for p in providers],
            "total": len(providers),
        }
    )

    best: Dict[str, DayForecast] = {}

    async def handle(provider: Provider, client: httpx.AsyncClient):
        try:
            days = await _cached_fetch(provider, client, lat, lon)
            return provider, days, "ok", None
        except Exception as exc:  # noqa: BLE001 - surface any provider failure
            return provider, [], "error", str(exc)

    async with httpx.AsyncClient(
        timeout=settings.http_timeout, follow_redirects=True
    ) as client:
        tasks = [asyncio.create_task(handle(p, client)) for p in providers]
        done = 0
        for coro in asyncio.as_completed(tasks):
            provider, days, status, error = await coro
            done += 1
            changed = merge_best(best, days, provider.name) if status == "ok" else False
            await emit(
                {
                    "type": "update",
                    "provider": provider.name,
                    "status": status,
                    "error": error,
                    "done": done,
                    "total": len(providers),
                    "changed": changed,
                    "days": _window(best),
                }
            )

    await emit({"type": "complete", "total": len(providers), "days": _window(best)})
