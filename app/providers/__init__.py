"""Registry of all weather providers.

Keyless providers always run. Key-based providers run only when their key is
configured (see each provider's `enabled`).
"""

from typing import List

from .base import Provider
from .bright_sky import BrightSky
from .met_norway import MetNorway
from .open_meteo import OpenMeteo
from .openweathermap import OpenWeatherMap
from .weatherapi import WeatherApiCom

ALL_PROVIDERS: List[Provider] = [
    OpenMeteo(),
    MetNorway(),
    BrightSky(),
    OpenWeatherMap(),
    WeatherApiCom(),
]


def active_providers() -> List[Provider]:
    """Providers that are currently enabled (keyless, or key configured)."""
    return [p for p in ALL_PROVIDERS if p.enabled()]
