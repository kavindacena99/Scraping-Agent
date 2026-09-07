from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from research.exceptions import BlockedURLError

from .url_validator import InvalidURLError, normalize_url, same_site


@dataclass(frozen=True)
class ExtractedLink:
    url: str
    anchor_text: str


class LinkExtractor:
    def extract_internal(self, html: str, page_url: str, root_url: str) -> list[ExtractedLink]:
        soup = BeautifulSoup(html or "", "html.parser")
        found: dict[str, ExtractedLink] = {}
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            try:
                url = normalize_url(urljoin(page_url, href))
            except (InvalidURLError, BlockedURLError):
                continue
            if not same_site(url, root_url):
                continue
            path = urlsplit(url).path.lower()
            if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".mp4", ".mp3")):
                continue
            text = " ".join(anchor.get_text(" ", strip=True).split())[:200]
            found.setdefault(url, ExtractedLink(url=url, anchor_text=text))
        return list(found.values())
