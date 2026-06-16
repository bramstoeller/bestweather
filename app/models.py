"""Normalized data models shared across providers."""

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class DayForecast:
    """One day of weather, normalized across every provider."""

    date: str  # ISO date, YYYY-MM-DD (local to the queried location)
    temp_max: float  # degrees Celsius
    temp_min: Optional[float] = None
    precip_mm: float = 0.0
    precip_prob: Optional[int] = None  # 0-100, if the provider reports it
    weather_code: Optional[int] = None  # WMO code, if available
    source: Optional[str] = None  # provider name that produced this day

    def to_dict(self) -> dict:
        return asdict(self)
