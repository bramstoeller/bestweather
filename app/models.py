"""Normalized data shared across providers."""

from dataclasses import asdict, dataclass
from typing import List, Optional


@dataclass
class DayForecast:
    date: str  # ISO date, local to the queried location
    temp_max: float
    temp_min: Optional[float] = None
    precip_mm: float = 0.0
    precip_prob: Optional[int] = None  # 0-100
    wind_kmh: Optional[float] = None
    weather_code: Optional[int] = None  # WMO code where available
    source: Optional[str] = None  # provider that produced this day
    score: Optional[float] = None  # profile score, set during merge
    hourly: Optional[List[dict]] = None  # per-hour breakdown, if available

    def to_dict(self) -> dict:
        return asdict(self)
