"""Visual Crossing: needs a free key. Up to 15 days."""

from typing import List

import httpx

from ..config import settings
from ..models import DayForecast
from .base import Provider


class VisualCrossing(Provider):
    name = "Visual Crossing"
    url = "https://www.visualcrossing.com"
    region = "global"
    requires_key = True

    def enabled(self) -> bool:
        return bool(settings.visualcrossing_key)

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        url = (
            "https://weather.visualcrossing.com/VisualCrossingWebServices"
            f"/rest/services/timeline/{lat},{lon}"
        )
        params = {
            "unitGroup": "metric",
            "include": "days",
            "key": settings.visualcrossing_key,
            "elements": "datetime,tempmax,tempmin,precip,precipprob,windspeed",
        }
        resp = await client.get(url, params=params)
        resp.raise_for_status()

        out: List[DayForecast] = []
        for d in resp.json().get("days", []):
            out.append(
                DayForecast(
                    date=d["datetime"],
                    temp_max=d.get("tempmax"),
                    temp_min=d.get("tempmin"),
                    precip_mm=float(d.get("precip") or 0.0),
                    precip_prob=int(d["precipprob"]) if d.get("precipprob") is not None else None,
                    wind_kmh=float(d["windspeed"]) if d.get("windspeed") is not None else None,
                )
            )
        return out
