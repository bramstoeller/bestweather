"""Application configuration, loaded from environment / .env file."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    openweathermap_key: str = _get("OPENWEATHERMAP_API_KEY")
    weatherapi_key: str = _get("WEATHERAPI_API_KEY")
    contact_email: str = _get("CONTACT_EMAIL", "info@mooisteweer.nl")
    cache_ttl_seconds: int = int(_get("CACHE_TTL_SECONDS", "1800"))
    geocode_cache_ttl_seconds: int = int(_get("GEOCODE_CACHE_TTL_SECONDS", "86400"))
    http_timeout: float = float(_get("HTTP_TIMEOUT", "12"))
    # How many days of forecast to show (today + N-1 ahead).
    forecast_days: int = 15


settings = Settings()
