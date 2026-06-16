"""Buienradar: keyless Dutch forecast. The feed is a national 5-day outlook."""

from typing import List, Optional

import httpx

from ..models import DayForecast
from .base import Provider


def _beaufort_to_kmh(bft) -> Optional[float]:
    if bft is None:
        return None
    return round(0.836 * (float(bft) ** 1.5) * 3.6, 1)


def _avg(*values) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    return sum(nums) / len(nums) if nums else None


class Buienradar(Provider):
    name = "Buienradar"
    url = "https://www.buienradar.nl"
    region = "nl"

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        resp = await client.get("https://data.buienradar.nl/2.0/feed/json")
        resp.raise_for_status()
        forecast = resp.json()["Forecast"]["FiveDayForecast"]

        out: List[DayForecast] = []
        for d in forecast:
            # Temperatures come as numeric Min/Max bound fields; the plain
            # MaxTemperature field is sometimes a "25/28" range string.
            temp_max = _avg(d.get("MaxTemperatureMin"), d.get("MaxTemperatureMax"))
            temp_min = _avg(d.get("MinTemperatureMin"), d.get("MinTemperatureMax"))
            if temp_max is None:
                continue
            precip = _avg(d.get("RainMinMm"), d.get("RainMaxMm")) or 0.0
            out.append(
                DayForecast(
                    date=str(d["Day"])[:10],
                    temp_max=round(temp_max, 1),
                    temp_min=round(temp_min, 1) if temp_min is not None else None,
                    precip_mm=round(precip, 1),
                    precip_prob=int(d["RainChance"]) if d.get("RainChance") is not None else None,
                    wind_kmh=_beaufort_to_kmh(d.get("WindBeaufort")),
                )
            )
        return out
