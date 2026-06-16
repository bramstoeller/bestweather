"""Weerlive.nl: needs a free key. Dutch forecast, a few days ahead."""

from typing import List, Optional

import httpx

from ..config import settings
from ..models import DayForecast
from .base import Provider


def _iso(dag: str) -> Optional[str]:
    # Weerlive returns dd-mm-yyyy.
    try:
        d, m, y = dag.split("-")
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    except (ValueError, AttributeError):
        return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Weerlive(Provider):
    name = "Weerlive.nl"
    url = "https://weerlive.nl"
    region = "nl"
    requires_key = True

    def enabled(self) -> bool:
        return bool(settings.weerlive_key)

    async def fetch(self, client, lat, lon) -> List[DayForecast]:
        params = {"key": settings.weerlive_key, "locatie": f"{lat},{lon}"}
        resp = await client.get("https://weerlive.nl/api/weerlive_api_v2.php", params=params)
        resp.raise_for_status()

        out: List[DayForecast] = []
        for d in resp.json().get("wk_verw", []):
            date = _iso(d.get("dag"))
            tmax = _num(d.get("max_temp"))
            if not date or tmax is None:
                continue
            prob = d.get("neersl_perc_dag")
            out.append(
                DayForecast(
                    date=date,
                    temp_max=tmax,
                    temp_min=_num(d.get("min_temp")),
                    precip_prob=int(prob) if prob not in (None, "") else None,
                    wind_kmh=_num(d.get("windkmh")),
                )
            )
        return out
