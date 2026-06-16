"""MET Norway (yr.no) — free, keyless, global. Hourly data aggregated to days.

MET requires an identifying User-Agent with contact info per their TOS.
"""

from typing import Dict, List

import httpx

from ..config import settings
from ..models import DayForecast
from .base import Provider


class MetNorway(Provider):
    name = "MET Norway"

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        headers = {"User-Agent": f"BestWeather/1.0 ({settings.contact_email})"}
        params = {"lat": round(lat, 4), "lon": round(lon, 4)}
        resp = await client.get(
            "https://api.met.no/weatherapi/locationforecast/2.0/compact",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        series = resp.json()["properties"]["timeseries"]

        # Aggregate the hourly time series into per-day min/max/precip.
        days: Dict[str, dict] = {}
        for entry in series:
            date = entry["time"][:10]
            details = entry["data"]["instant"]["details"]
            temp = details.get("air_temperature")

            precip = 0.0
            next_1h = entry["data"].get("next_1_hours")
            next_6h = entry["data"].get("next_6_hours")
            if next_1h:
                precip = next_1h["details"].get("precipitation_amount", 0.0)
            elif next_6h:
                precip = next_6h["details"].get("precipitation_amount", 0.0)

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
