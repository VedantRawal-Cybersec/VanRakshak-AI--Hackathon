from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class PhotonAdapter(BaseAdapter):
    name = "photon"
    source_url = "https://photon.komoot.io/"

    @staticmethod
    def _normalize(data: dict):
        out=[]
        for f in data.get("features") or []:
            geom=f.get("geometry") or {}
            coords=geom.get("coordinates") or []
            if len(coords) < 2:
                continue
            p=f.get("properties") or {}
            parts=[p.get("name"),p.get("city"),p.get("district"),p.get("state"),p.get("country")]
            out.append({
                "lat": str(coords[1]),
                "lon": str(coords[0]),
                "display_name": ", ".join(str(x) for x in parts if x),
                "address": {
                    "city": p.get("city"),
                    "county": p.get("county") or p.get("district"),
                    "state": p.get("state"),
                    "country": p.get("country"),
                    "country_code": p.get("countrycode"),
                },
                "geojson": geom,
                "_fallback_source": "Photon/OpenStreetMap",
            })
        return out

    async def search(self, q: str, limit: int = 5):
        params={"q":q,"limit":min(max(limit,1),10),"lang":"en","lat":20.5937,"lon":78.9629}
        return self._normalize(await self.get_json(settings.photon_url.rstrip("/") + "/api", params=params))

    async def reverse(self, lat: float, lon: float):
        data=await self.get_json(settings.photon_url.rstrip("/") + "/reverse", params={"lat":lat,"lon":lon,"lang":"en"})
        rows=self._normalize(data)
        return rows[0] if rows else {}
