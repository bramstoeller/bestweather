"""Open-Meteo: keyless global forecasts. Also exposes individual models (ECMWF,
GFS, ...) as separate sources, and supplies the hourly breakdown."""

from collections import defaultdict
from typing import List, Optional

import httpx

from ..models import DayForecast
from .base import Provider

_DAILY = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,weather_code,wind_speed_10m_max"
)
_HOURLY = "temperature_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m"


class OpenMeteo(Provider):
    url = "https://open-meteo.com"
    region = "global"

    def __init__(self, name: str = "Open-Meteo", model: Optional[str] = None,
                 hourly: bool = False, region: str = "global"):
        self.name = name
        self.model = model
        self.with_hourly = hourly
        self.region = region

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": _DAILY,
            "forecast_days": 16,
            "timezone": "auto",
        }
        if self.model:
            params["models"] = self.model
        if self.with_hourly:
            params["hourly"] = _HOURLY

        resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        resp.raise_for_status()
        data = resp.json()
        daily = data["daily"]

        days: List[DayForecast] = []
        for i, date in enumerate(daily["time"]):
            days.append(
                DayForecast(
                    date=date,
                    temp_max=daily["temperature_2m_max"][i],
                    temp_min=daily["temperature_2m_min"][i],
                    precip_mm=daily["precipitation_sum"][i] or 0.0,
                    precip_prob=daily["precipitation_probability_max"][i],
                    wind_kmh=daily["wind_speed_10m_max"][i],
                    weather_code=daily["weather_code"][i],
                )
            )

        if self.with_hourly and "hourly" in data:
            _attach_hourly(days, data["hourly"])
        return days


class OpenMeteoEnsemble(Provider):
    """Many national models in one request, exposed as one source per model."""

    url = "https://open-meteo.com"
    region = "global"
    requires_key = False

    def __init__(self, models):
        self.name = "Open-Meteo ensemble"
        self.models = models  # list of (display_name, model_id, region)

    def sources(self):
        return [{"name": n, "url": self.url, "keyless": True, "region": r} for n, _, r in self.models]

    async def fetch_sources(self, client, lat, lon):
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": _DAILY,
            "forecast_days": 16,
            "timezone": "auto",
            "models": ",".join(m for _, m, _ in self.models),
        }
        resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        resp.raise_for_status()
        daily = resp.json()["daily"]
        times = daily["time"]

        out = {}
        for name, mid, _ in self.models:
            tmax = daily.get(f"temperature_2m_max_{mid}")
            if not tmax or all(v is None for v in tmax):
                continue
            tmin = daily.get(f"temperature_2m_min_{mid}")
            psum = daily.get(f"precipitation_sum_{mid}")
            pprob = daily.get(f"precipitation_probability_max_{mid}")
            wind = daily.get(f"wind_speed_10m_max_{mid}")
            code = daily.get(f"weather_code_{mid}")
            days = []
            for i, date in enumerate(times):
                if tmax[i] is None:
                    continue
                days.append(
                    DayForecast(
                        date=date,
                        temp_max=tmax[i],
                        temp_min=tmin[i] if tmin else None,
                        precip_mm=(psum[i] if psum and psum[i] is not None else 0.0),
                        precip_prob=(pprob[i] if pprob else None),
                        wind_kmh=(wind[i] if wind else None),
                        weather_code=(code[i] if code else None),
                    )
                )
            if days:
                out[name] = days
        return out


def _attach_hourly(days: List[DayForecast], hourly: dict) -> None:
    buckets = defaultdict(list)
    for i, ts in enumerate(hourly["time"]):
        buckets[ts[:10]].append(
            {
                "time": ts[11:16],
                "temp": hourly["temperature_2m"][i],
                "precip": hourly["precipitation"][i],
                "prob": hourly["precipitation_probability"][i],
                "wind": hourly["wind_speed_10m"][i],
                "code": hourly["weather_code"][i],
            }
        )
    for d in days:
        if d.date in buckets:
            d.hourly = buckets[d.date]
