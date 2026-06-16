"""Bright Sky (DWD): keyless, strongest around Germany. Hourly aggregated to days."""

from datetime import date as date_cls
from datetime import timedelta
from typing import Dict, List

import httpx

from ..models import DayForecast
from .base import Provider


class BrightSky(Provider):
    name = "Bright Sky (DWD)"
    url = "https://brightsky.dev"
    region = "de"

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        today = date_cls.today()
        params = {
            "lat": lat,
            "lon": lon,
            "date": today.isoformat(),
            "last_date": (today + timedelta(days=10)).isoformat(),
        }
        resp = await client.get("https://api.brightsky.dev/weather", params=params)
        resp.raise_for_status()
        records = resp.json().get("weather", [])

        days: Dict[str, dict] = {}
        for rec in records:
            date = rec["timestamp"][:10]
            temp = rec.get("temperature")
            wind = rec.get("wind_speed")  # km/h
            day = days.setdefault(date, {"tmax": None, "tmin": None, "precip": 0.0, "wind": None})
            if temp is not None:
                day["tmax"] = temp if day["tmax"] is None else max(day["tmax"], temp)
                day["tmin"] = temp if day["tmin"] is None else min(day["tmin"], temp)
            if wind is not None:
                day["wind"] = wind if day["wind"] is None else max(day["wind"], wind)
            day["precip"] += rec.get("precipitation") or 0.0

        out: List[DayForecast] = []
        for date in sorted(days):
            v = days[date]
            if v["tmax"] is None:
                continue
            out.append(
                DayForecast(
                    date=date,
                    temp_max=round(v["tmax"], 1),
                    temp_min=round(v["tmin"], 1) if v["tmin"] is not None else None,
                    precip_mm=round(v["precip"], 2),
                    wind_kmh=round(v["wind"], 1) if v["wind"] is not None else None,
                )
            )
        return out
