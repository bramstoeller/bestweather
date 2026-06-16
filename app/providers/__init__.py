"""Provider registry. Keyless providers always run; key-based ones run when their
key is configured."""

from typing import List

from .base import Provider
from .bright_sky import BrightSky
from .buienradar import Buienradar
from .met_norway import MetNorway
from .open_meteo import OpenMeteo
from .openweathermap import OpenWeatherMap
from .tomorrow import TomorrowIo
from .visualcrossing import VisualCrossing
from .weatherapi import WeatherApiCom
from .weerlive import Weerlive
from .wttr import WttrIn

ALL_PROVIDERS: List[Provider] = [
    OpenMeteo(hourly=True),
    OpenMeteo("ECMWF", "ecmwf_ifs025"),
    OpenMeteo("GFS (NOAA)", "gfs_seamless"),
    MetNorway(),
    BrightSky(),
    Buienradar(),
    WttrIn(),
    OpenWeatherMap(),
    WeatherApiCom(),
    TomorrowIo(),
    VisualCrossing(),
    Weerlive(),
]


def active_providers() -> List[Provider]:
    return [p for p in ALL_PROVIDERS if p.enabled()]


def sources_meta() -> List[dict]:
    return [
        {"name": p.name, "url": p.url, "keyless": not p.requires_key, "region": p.region}
        for p in active_providers()
    ]
