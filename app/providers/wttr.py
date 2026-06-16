"""wttr.in: keyless, global. Roughly 3 days."""

from typing import List

import httpx

from ..models import DayForecast
from .base import Provider


class WttrIn(Provider):
    name = "wttr.in"
    url = "https://wttr.in"
    region = "global"

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        resp = await client.get(
            f"https://wttr.in/{lat},{lon}",
            params={"format": "j1"},
            headers={"User-Agent": "curl/8"},
        )
        resp.raise_for_status()

        out: List[DayForecast] = []
        for d in resp.json().get("weather", []):
            hours = d.get("hourly", [])
            precip = sum(float(h.get("precipMM", 0) or 0) for h in hours)
            probs = [int(h.get("chanceofrain", 0) or 0) for h in hours]
            winds = [float(h.get("windspeedKmph", 0) or 0) for h in hours]
            out.append(
                DayForecast(
                    date=d["date"],
                    temp_max=float(d["maxtempC"]),
                    temp_min=float(d["mintempC"]),
                    precip_mm=round(precip, 1),
                    precip_prob=max(probs) if probs else None,
                    wind_kmh=max(winds) if winds else None,
                )
            )
        return out
