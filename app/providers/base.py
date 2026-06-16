"""Provider interface.

Most providers are a single source: `fetch` returns one list of DayForecast.
A provider may also stand for several sources at once (e.g. one Open-Meteo
request covering many models); it then overrides `sources` and `fetch_sources`.
"""

from typing import Dict, List

import httpx

from ..models import DayForecast


class Provider:
    name: str = "base"
    url: str = ""
    region: str = "global"  # global | a country code
    requires_key: bool = False

    def enabled(self) -> bool:
        return True

    def sources(self) -> List[dict]:
        return [{"name": self.name, "url": self.url, "keyless": not self.requires_key, "region": self.region}]

    async def fetch(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> List[DayForecast]:
        raise NotImplementedError

    async def fetch_sources(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> Dict[str, List[DayForecast]]:
        return {self.name: await self.fetch(client, lat, lon)}
