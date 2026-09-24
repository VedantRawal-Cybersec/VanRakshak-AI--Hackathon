from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class GDELTAdapter(BaseAdapter):
    name = "gdelt"
    source_url = "https://www.gdeltproject.org/"

    async def forest_news(self, place: str, timespan: str = "1week", maxrecords: int = 25):
        query = f'"{place}" (deforestation OR logging OR "forest fire" OR encroachment OR mining OR "tree felling" OR "forest clearing")'
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "sort": "datedesc",
            "timespan": timespan,
            "maxrecords": maxrecords,
        }
        return await self.get_json(settings.gdelt_url, params=params)
