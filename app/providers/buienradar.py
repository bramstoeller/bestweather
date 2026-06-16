"""Buienradar: keyless Dutch forecast. The feed is a national 5-day outlook.

Buienradar's JSON has shipped with both PascalCase and lowercase keys, so we
lower-case every key before reading it.
"""

from typing import List, Optional

import httpx

from ..models import DayForecast
from .base import Provider


def _lower(d: dict) -> dict:
    return {k.lower(): v for k, v in d.items()} if isinstance(d, dict) else {}


def _num(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _avg(*values) -> Optional[float]:
    nums = [n for n in (_num(v) for v in values) if n is not None]
    return sum(nums) / len(nums) if nums else None


def _beaufort_to_kmh(bft) -> Optional[float]:
    n = _num(bft)
    return round(0.836 * (n ** 1.5) * 3.6, 1) if n is not None else None


class Buienradar(Provider):
    name = "Buienradar"
    url = "https://www.buienradar.nl"
    region = "nl"

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        resp = await client.get("https://data.buienradar.nl/2.0/feed/json")
        resp.raise_for_status()
        root = _lower(resp.json())
        forecast = _lower(root.get("forecast"))
        days_in = forecast.get("fivedayforecast") or []

        out: List[DayForecast] = []
        for entry in days_in:
            d = _lower(entry)
            temp_max = _avg(d.get("maxtemperaturemin"), d.get("maxtemperaturemax"))
            temp_min = _avg(d.get("mintemperaturemin"), d.get("mintemperaturemax"))
            if temp_max is None:
                temp_max = _num(d.get("maxtemperature"))
                temp_min = _num(d.get("mintemperature"))
            if temp_max is None:
                continue
            precip = _avg(d.get("mmrainmin"), d.get("mmrainmax")) or 0.0
            rain_chance = d.get("rainchance")
            out.append(
                DayForecast(
                    date=str(d.get("day"))[:10],
                    temp_max=round(temp_max, 1),
                    temp_min=round(temp_min, 1) if temp_min is not None else None,
                    precip_mm=round(precip, 1),
                    precip_prob=int(rain_chance) if rain_chance is not None else None,
                    wind_kmh=_beaufort_to_kmh(d.get("windbeaufort", d.get("wind"))),
                )
            )
        return out
