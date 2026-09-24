from __future__ import annotations
from app.adapters.base import BaseAdapter

class GFWAdapter(BaseAdapter):
    name = "global_forest_watch"
    source_url = "https://www.globalforestwatch.org/"

    async def metadata(self):
        # Public GFW products are surfaced as map/tiles and data APIs. This adapter exposes
        # stable source metadata; dataset-specific access can be configured without fake values.
        return {
            "name": "Global Forest Watch",
            "tiles": "https://tiles.globalforestwatch.org/",
            "data_api_repo": "https://github.com/wri/gfw-data-api",
            "note": "Configure the exact public disturbance layer/data endpoint approved for deployment."
        }
