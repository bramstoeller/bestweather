"""Provider interface. Every source returns a normalized list of DayForecast."""

from typing import List

import httpx

from ..models import DayForecast


class Provider:
    name: str = "base"
    url: str = ""
    region: str = "global"  # global | nl | de
    requires_key: bool = False

    def enabled(self) -> bool:
        return True

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        raise NotImplementedError
