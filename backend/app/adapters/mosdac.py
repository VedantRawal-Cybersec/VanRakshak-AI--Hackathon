from __future__ import annotations
from app.adapters.base import BaseAdapter, AdapterError


class MOSDACAdapter(BaseAdapter):
    """Safe integration helper for the official MOSDAC Data Download API workflow.

    MOSDAC's current public manual distributes an official `mdapi.py` client. Search does not
    require authentication, while downloads require a MOSDAC account. We intentionally do not
    reimplement undocumented private endpoints: this adapter validates and produces the exact
    official config.json payload that can be handed to the sanctioned client/worker.
    """
    name = "isro_mosdac"
    source_url = "https://mosdac.gov.in/"
    catalog_url = "https://mosdac.gov.in/catalog-app/satellite.php"
    manual_url = "https://mosdac.gov.in/downloadapi-manual"
    client_url = "https://mosdac.gov.in/software/mdapi.zip"

    @staticmethod
    def config(dataset_id: str, start_time: str = "", end_time: str = "", count: int = 50,
               bounding_box: str = "", granule_id: str = "", download_path: str = "./data/mosdac",
               username: str = "", password: str = "", download: bool = False) -> dict:
        dataset_id = (dataset_id or "").strip()
        if not dataset_id or len(dataset_id) > 120:
            raise AdapterError("datasetId is required and must be <= 120 characters")
        if count < 1 or count > 100:
            raise AdapterError("MOSDAC count must be between 1 and 100")
        if bounding_box:
            try:
                vals=[float(x.strip()) for x in bounding_box.split(",")]
                if len(vals)!=4: raise ValueError
                minlon,minlat,maxlon,maxlat=vals
                if not (-180<=minlon<maxlon<=180 and -90<=minlat<maxlat<=90): raise ValueError
            except Exception as e:
                raise AdapterError("boundingBox must be minLon,minLat,maxLon,maxLat") from e
        return {
            "user_credentials": {"username": username if download else "", "password": password if download else ""},
            "search_parameters": {
                "datasetId": dataset_id, "startTime": start_time, "endTime": end_time,
                "count": str(count), "boundingBox": bounding_box, "gId": granule_id,
            },
            "download_settings": {
                "download_path": download_path, "organize_by_date": True,
                "skip_user_prompt": True, "generate_error_log": True,
                "error_log_path": "./logs/mosdac",
            },
        }
