"""Tomorrow.io: needs a free key. Daily timeline."""

from typing import List, Optional

import httpx

from ..config import settings
from ..models import DayForecast
from .base import Provider


def _int(v) -> Optional[int]:
    return int(round(v)) if v is not None else None


class TomorrowIo(Provider):
    name = "Tomorrow.io"
    url = "https://www.tomorrow.io"
    region = "global"
    requires_key = True

    def enabled(self) -> bool:
        return bool(settings.tomorrow_key)

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        params = {
            "location": f"{lat},{lon}",
            "timesteps": "1d",
            "units": "metric",
            "apikey": settings.tomorrow_key,
        }
        resp = await client.get("https://api.tomorrow.io/v4/weather/forecast", params=params)
        resp.raise_for_status()

        out: List[DayForecast] = []
        for entry in resp.json()["timelines"]["daily"]:
            v = entry["values"]
            wind = v.get("windSpeedMax", v.get("windSpeedAvg"))
            prob = v.get("precipitationProbabilityMax", v.get("precipitationProbabilityAvg"))
            out.append(
                DayForecast(
                    date=entry["time"][:10],
                    temp_max=v.get("temperatureMax"),
                    temp_min=v.get("temperatureMin"),
                    precip_mm=float(v.get("rainAccumulationSum", 0.0) or 0.0),
                    precip_prob=_int(prob),
                    wind_kmh=round(float(wind) * 3.6, 1) if wind is not None else None,
                )
            )
        return out
