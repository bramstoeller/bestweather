"""Open-Meteo — free, keyless, up to 16 days of daily forecast worldwide."""

from typing import List

import httpx

from ..models import DayForecast
from .base import Provider


class OpenMeteo(Provider):
    name = "Open-Meteo"

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "weather_code",
                ]
            ),
            "forecast_days": 16,
            "timezone": "auto",
        }
        resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        resp.raise_for_status()
        daily = resp.json()["daily"]

        out: List[DayForecast] = []
        for i, date in enumerate(daily["time"]):
            out.append(
                DayForecast(
                    date=date,
                    temp_max=daily["temperature_2m_max"][i],
                    temp_min=daily["temperature_2m_min"][i],
                    precip_mm=daily["precipitation_sum"][i] or 0.0,
                    precip_prob=daily["precipitation_probability_max"][i],
                    weather_code=daily["weather_code"][i],
                )
            )
        return out
