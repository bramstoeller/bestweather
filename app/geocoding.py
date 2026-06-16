"""Location search (forward) and reverse geocoding, using free keyless APIs."""

from typing import List, Optional

import httpx

from .cache import cache
from .config import settings


async def search(query: str, lang: str = "en", limit: int = 8) -> List[dict]:
    """Search places by name via Open-Meteo's keyless geocoding API."""
    query = query.strip()
    if not query:
        return []

    key = f"geo-search:{lang}:{query.lower()}"
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

    out = [
        {
            "name": r["name"],
            "admin1": r.get("admin1"),
            "country": r.get("country"),
            "country_code": r.get("country_code"),
            "lat": r["latitude"],
            "lon": r["longitude"],
        }
        for r in results
    ]
    await cache.set(key, out, settings.geocode_cache_ttl_seconds)
    return out


async def reverse(lat: float, lon: float, lang: str = "en") -> Optional[dict]:
    """Resolve coordinates to a place name via BigDataCloud's keyless API."""
    key = f"geo-reverse:{lang}:{round(lat, 3)}:{round(lon, 3)}"
    cached = await cache.get(key)
    if cached is not None:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "localityLanguage": lang,
    }
    async with httpx.AsyncClient(
        timeout=settings.http_timeout, follow_redirects=True
    ) as client:
        resp = await client.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client", params=params
        )
        resp.raise_for_status()
        data = resp.json()

    name = data.get("city") or data.get("locality") or data.get("principalSubdivision")
    out = {
        "name": name or "Current location",
        "admin1": data.get("principalSubdivision"),
        "country": data.get("countryName"),
        "country_code": data.get("countryCode"),
        "lat": lat,
        "lon": lon,
    }
    await cache.set(key, out, settings.geocode_cache_ttl_seconds)
    return out
