"""WeatherAPI.com — optional, needs a free API key. Up to 14 daily forecasts."""

from typing import List

import httpx

from ..config import settings
from ..models import DayForecast
from .base import Provider


class WeatherApiCom(Provider):
    name = "WeatherAPI.com"
    requires_key = True

    def enabled(self) -> bool:
        return bool(settings.weatherapi_key)

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        params = {
            "key": settings.weatherapi_key,
            "q": f"{lat},{lon}",
            "days": 14,
        }
        resp = await client.get(
            "https://api.weatherapi.com/v1/forecast.json", params=params
        )
        resp.raise_for_status()

        out: List[DayForecast] = []
        for fc in resp.json()["forecast"]["forecastday"]:
            day = fc["day"]
            out.append(
                DayForecast(
                    date=fc["date"],
                    temp_max=day["maxtemp_c"],
                    temp_min=day["mintemp_c"],
                    precip_mm=float(day.get("totalprecip_mm", 0.0)),
                    precip_prob=int(day.get("daily_chance_of_rain", 0)),
                )
            )
        return out
