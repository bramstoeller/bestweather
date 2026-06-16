"""OpenWeatherMap — optional, needs a free API key (One Call 3.0, 8 days)."""

from datetime import datetime, timezone
from typing import List

import httpx

from ..config import settings
from ..models import DayForecast
from .base import Provider


class OpenWeatherMap(Provider):
    name = "OpenWeatherMap"
    requires_key = True

    def enabled(self) -> bool:
        return bool(settings.openweathermap_key)

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "current,minutely,hourly,alerts",
            "units": "metric",
            "appid": settings.openweathermap_key,
        }
        resp = await client.get(
            "https://api.openweathermap.org/data/3.0/onecall", params=params
        )
        resp.raise_for_status()

        out: List[DayForecast] = []
        for day in resp.json().get("daily", []):
            date = datetime.fromtimestamp(day["dt"], tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
            precip = float(day.get("rain", 0.0)) + float(day.get("snow", 0.0))
            out.append(
                DayForecast(
                    date=date,
                    temp_max=day["temp"]["max"],
                    temp_min=day["temp"]["min"],
                    precip_mm=round(precip, 2),
                    precip_prob=int(round(day.get("pop", 0.0) * 100)),
                )
            )
        return out
