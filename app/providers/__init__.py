"""Provider registry. Keyless providers always run; key-based ones run when their
key is configured.

The bulk of the sources are individual numerical weather models from national
meteorological services worldwide, served through Open-Meteo. Each model is an
independent forecast, so querying them all is exactly what "the best of every
source" needs.
"""

from typing import List

from .base import Provider
from .bright_sky import BrightSky
from .buienradar import Buienradar
from .met_norway import MetNorway
from .open_meteo import OpenMeteo, OpenMeteoEnsemble
from .openweathermap import OpenWeatherMap
from .tomorrow import TomorrowIo
from .visualcrossing import VisualCrossing
from .weatherapi import WeatherApiCom
from .weerlive import Weerlive
from .wttr import WttrIn

# (display name, Open-Meteo model id, region tag) for each agency model.
OPENMETEO_MODELS = [
    ("ECMWF", "ecmwf_ifs025", "eu"),
    ("ECMWF AIFS", "ecmwf_aifs025_single", "eu"),
    ("GFS · NOAA", "gfs_seamless", "us"),
    ("GFS Global · NOAA", "gfs_global", "us"),
    ("ICON · DWD", "icon_seamless", "de"),
    ("ICON Global · DWD", "icon_global", "de"),
    ("ICON-EU · DWD", "icon_eu", "de"),
    ("ICON-D2 · DWD", "icon_d2", "de"),
    ("GEM · Canada", "gem_seamless", "ca"),
    ("GEM Global · Canada", "gem_global", "ca"),
    ("GEM Regional · Canada", "gem_regional", "ca"),
    ("Météo-France", "meteofrance_seamless", "fr"),
    ("ARPEGE World", "meteofrance_arpege_world", "fr"),
    ("ARPEGE Europe", "meteofrance_arpege_europe", "fr"),
    ("AROME France", "meteofrance_arome_france", "fr"),
    ("AROME France HD", "meteofrance_arome_france_hd", "fr"),
    ("JMA · Japan", "jma_seamless", "jp"),
    ("GSM · JMA", "jma_gsm", "jp"),
    ("MET Nordic", "metno_seamless", "no"),
    ("KNMI", "knmi_seamless", "nl"),
    ("HARMONIE NL · KNMI", "knmi_harmonie_arome_netherlands", "nl"),
    ("HARMONIE EU · KNMI", "knmi_harmonie_arome_europe", "nl"),
    ("DMI · Denmark", "dmi_seamless", "dk"),
    ("HARMONIE · DMI", "dmi_harmonie_arome_europe", "dk"),
    ("UK Met Office", "ukmo_seamless", "uk"),
    ("UKMO Global", "ukmo_global_deterministic_10km", "uk"),
    ("UKMO UK 2km", "ukmo_uk_deterministic_2km", "uk"),
    ("GRAPES · CMA", "cma_grapes_global", "cn"),
]

ALL_PROVIDERS: List[Provider] = [
    OpenMeteo(hourly=True),  # Open-Meteo's blended best match; also supplies hourly
    OpenMeteoEnsemble(OPENMETEO_MODELS),  # all national models in one request
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
    out: List[dict] = []
    for p in active_providers():
        out.extend(p.sources())
    return out
