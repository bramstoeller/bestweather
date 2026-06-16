"""Place search (forward) and reverse geocoding, using free keyless APIs."""

from typing import List, Optional

import httpx

from .cache import cache
from .config import settings


async def search(query: str, lang: str = "en", limit: int = 8) -> List[dict]:
    """Search places by name via Open-Meteo's keyless geocoding API."""
    query = query.strip()
    if not query:
        return []

    key = f"geo-search:{lang}:{query.lower()}:{limit}"
    cached = await cache.get(key)
    if cached is not None:
        return cached

    params = {"name": query, "count": limit, "language": lang, "format": "json"}
    async with httpx.AsyncClient(
        timeout=settings.http_timeout, follow_redirects=True
    ) as client:
        resp = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search", params=params
        )
        resp.raise_for_status()
        results = resp.json().get("results", []) or []

    out = [_place(r) for r in results]
    await cache.set(key, out, settings.geocode_cache_ttl_seconds)
    return out


async def reverse(lat: float, lon: float, lang: str = "en") -> Optional[dict]:
    """Resolve coordinates to a place.

    BigDataCloud turns coordinates into a locality name; that name is then run
    back through the search API so the result is named exactly like search
    results (canonical country/region names), without per-name special-casing.
    """
    key = f"geo-reverse:{lang}:{round(lat, 3)}:{round(lon, 3)}"
    cached = await cache.get(key)
    if cached is not None:
        return cached

    params = {"latitude": lat, "longitude": lon, "localityLanguage": lang}
    async with httpx.AsyncClient(
        timeout=settings.http_timeout, follow_redirects=True
    ) as client:
        resp = await client.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client", params=params
        )
        resp.raise_for_status()
        data = resp.json()

    name = data.get("city") or data.get("locality") or data.get("principalSubdivision")
    place = None
    if name:
        candidates = await search(name, lang, limit=10)
        place = _nearest(candidates, lat, lon)
    if place is None:
        place = {
            "name": name or "?",
            "admin1": data.get("principalSubdivision"),
            "country": data.get("countryName"),
            "country_code": data.get("countryCode"),
            "lat": lat,
            "lon": lon,
        }

    await cache.set(key, place, settings.geocode_cache_ttl_seconds)
    return place


def _place(r: dict) -> dict:
    return {
        "name": r["name"],
        "admin1": r.get("admin1"),
        "country": r.get("country"),
        "country_code": r.get("country_code"),
        "lat": r["latitude"],
        "lon": r["longitude"],
    }


def _nearest(candidates: List[dict], lat: float, lon: float, max_deg: float = 0.75):
    """Closest candidate to the coordinates, or None if all are far away."""
    best, best_d = None, max_deg ** 2
    for c in candidates:
        d = (c["lat"] - lat) ** 2 + (c["lon"] - lon) ** 2
        if d < best_d:
            best, best_d = c, d
    return best
