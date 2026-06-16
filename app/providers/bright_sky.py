"""Bright Sky (DWD) — free, keyless. Best coverage in/around Germany.

Returns hourly observations/forecasts which we aggregate to days. Outside its
coverage it simply returns little or nothing, which we handle gracefully.
"""

from datetime import date as date_cls
from datetime import timedelta
from typing import Dict, List

import httpx

from ..models import DayForecast
from .base import Provider


class BrightSky(Provider):
    name = "Bright Sky (DWD)"

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        today = date_cls.today()
        last = today + timedelta(days=10)
        params = {
            "lat": lat,
            "lon": lon,
            "date": today.isoformat(),
            "last_date": last.isoformat(),
        }
        resp = await client.get("https://api.brightsky.dev/weather", params=params)
        resp.raise_for_status()
        records = resp.json().get("weather", [])

        days: Dict[str, dict] = {}
        for rec in records:
            date = rec["timestamp"][:10]
            temp = rec.get("temperature")
            precip = rec.get("precipitation") or 0.0
            day = days.setdefault(date, {"tmax": None, "tmin": None, "precip": 0.0})
            if temp is not None:
                day["tmax"] = temp if day["tmax"] is None else max(day["tmax"], temp)
                day["tmin"] = temp if day["tmin"] is None else min(day["tmin"], temp)
            day["precip"] += precip

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
                )
            )
        return out
