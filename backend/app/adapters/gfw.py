from __future__ import annotations
from urllib.parse import urlencode
from app.adapters.base import BaseAdapter, AdapterError

class GFWAdapter(BaseAdapter):
    name = "global_forest_watch"
    source_url = "https://tiles.globalforestwatch.org/"

    async def metadata(self):
        return {
            "name": "Global Forest Watch",
            "tiles": "https://tiles.globalforestwatch.org/",
            "integrated_alerts": "gfw_integrated_alerts/latest/dynamic/{z}/{x}/{y}.png",
            "tree_cover_loss": "umd_tree_cover_loss/latest/dynamic/{z}/{x}/{y}.png",
            "glad_s2": "umd_glad_sentinel2_alerts/latest/dynamic/{z}/{x}/{y}.png",
            "note": "Public GFW tile-cache endpoints are used directly with the version alias latest."
        }

    def tile_layer(self, dataset: str = "gfw_integrated_alerts", start_date: str | None = None, end_date: str | None = None, confidence: str = "high"):
        allowed = {
            "gfw_integrated_alerts", "gfw_integrated_dist_alerts", "umd_glad_sentinel2_alerts",
            "umd_glad_landsat_alerts", "wur_radd_alerts", "umd_tree_cover_loss", "umd_tree_cover_loss_from_fires",
            "umd_tree_cover_gain", "umd_tree_cover_density_2000", "umd_tree_cover_height_2020"
        }
        if dataset not in allowed:
            raise AdapterError(f"Unsupported GFW raster dataset: {dataset}")
        url = f"https://tiles.globalforestwatch.org/{dataset}/latest/dynamic/{{z}}/{{x}}/{{y}}.png"
        params = []
        if start_date: params.append(("start_date", start_date))
        if end_date: params.append(("end_date", end_date))
        if dataset in {"gfw_integrated_alerts", "gfw_integrated_dist_alerts"}:
            params.extend([("render_type", "true_color"), ("alert_confidence", confidence)])
        elif dataset == "wur_radd_alerts":
            params.append(("confirmed_only", "true"))
        elif "alerts" in dataset:
            params.append(("confirmed_only", "true"))
        if params: url += "?" + urlencode(params)
        return {
            "dataset": dataset, "version": "latest", "tile_url": url,
            "source": "Global Forest Watch Tile Cache", "freshness": "DYNAMIC_RECENT",
            "attribution": "Global Forest Watch / underlying data providers"
        }
