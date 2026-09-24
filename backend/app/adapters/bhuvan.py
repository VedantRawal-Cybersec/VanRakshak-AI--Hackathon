from __future__ import annotations
import math
import re
from urllib.parse import urlencode
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

_LAYER_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


def xyz_bbox_wgs84(z: int, x: int, y: int) -> tuple[float,float,float,float]:
    if z < 0 or x < 0 or y < 0 or x >= 2**z or y >= 2**z:
        raise AdapterError("Invalid XYZ tile coordinates")
    n = 2.0 ** z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return west, south, east, north


class BhuvanAdapter(BaseAdapter):
    name = "isro_bhuvan_wms"
    source_url = "https://bhuvan.nrsc.gov.in/"

    def validate_layer(self, layer: str) -> str:
        if not _LAYER_RE.fullmatch(layer or ""):
            raise AdapterError("Invalid Bhuvan WMS layer name")
        return layer

    def tile_request_url(self, z: int, x: int, y: int, layer: str) -> str:
        layer = self.validate_layer(layer)
        west, south, east, north = xyz_bbox_wgs84(z, x, y)
        q = {
            "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
            "LAYERS": layer, "STYLES": "", "FORMAT": "image/png", "TRANSPARENT": "TRUE",
            "SRS": "EPSG:4326", "BBOX": f"{west},{south},{east},{north}",
            "WIDTH": "256", "HEIGHT": "256",
        }
        return f"{settings.bhuvan_wms_url}?{urlencode(q)}"

    async def tile(self, z: int, x: int, y: int, layer: str) -> tuple[bytes,str]:
        url = self.tile_request_url(z, x, y, layer)
        data, ctype = await self.get_bytes(url)
        if not ctype.startswith("image/"):
            # WMS servers often return XML ServiceException documents with HTTP 200.
            snippet = data[:400].decode("utf-8", "replace")
            raise AdapterError(f"Bhuvan WMS did not return an image: {snippet}")
        return data, ctype

    async def capabilities(self) -> str:
        return await self.get_text(settings.bhuvan_wms_url, params={
            "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetCapabilities"
        })
