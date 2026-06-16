"""Provider interface. Every weather source implements `fetch`."""

from typing import List

import httpx

from ..models import DayForecast


class Provider:
    """Base class for a weather source.

    Subclasses set `name`, optionally `requires_key`, and implement `fetch`,
    which returns a normalized list of DayForecast (one per day) or raises.
    """

    name: str = "base"
    requires_key: bool = False

    def enabled(self) -> bool:
        """Whether this provider should run (e.g. has a configured API key)."""
        return True

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        raise NotImplementedError
