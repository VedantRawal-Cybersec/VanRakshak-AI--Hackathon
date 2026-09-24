from __future__ import annotations

from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from app.adapters.base import BaseAdapter, AdapterError


class GoogleNewsRSSAdapter(BaseAdapter):
    """Credential-free recent-news fallback.

    Only public RSS metadata is returned: title, publisher/domain, timestamp and
    the article link. Article bodies are never scraped or copied.
    """

    name = "google_news_rss"
    source_url = "https://news.google.com/rss"

    async def forest_news(self, place: str, timespan: str = "1week", maxrecords: int = 25):
        # Google News RSS does not support GDELT-style timespan directly. Add a
        # search recency operator that Google understands while keeping the
        # output schema compatible with the GDELT adapter.
        recency = {
            "1day": "when:1d",
            "24h": "when:1d",
            "1week": "when:7d",
            "7days": "when:7d",
            "1month": "when:30d",
            "30days": "when:30d",
        }.get((timespan or "").lower(), "when:7d")
        query = f'"{place}" (deforestation OR logging OR "forest fire" OR encroachment OR mining OR "tree felling" OR "forest clearing") {recency}'
        url = (
            f"{self.source_url}/search?q={quote_plus(query)}"
            "&hl=en-IN&gl=IN&ceid=IN:en"
        )
        text = await self.get_text(url)
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise AdapterError("Google News RSS returned invalid XML") from exc

        articles = []
        for item in root.findall("./channel/item")[: max(1, min(int(maxrecords), 50))]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            domain = ""
            if source_el is not None:
                domain = (source_el.text or "").strip()
            seen = pub
            if pub:
                try:
                    seen = parsedate_to_datetime(pub).isoformat()
                except Exception:
                    pass
            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                    "domain": domain,
                    "seendate": seen,
                    "source": "Google News RSS",
                })
        return {
            "articles": articles,
            "query": query,
            "source": "Google News RSS",
            "note": "Recent article metadata only; news is contextual evidence and never proof of causation.",
        }
