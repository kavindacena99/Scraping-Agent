from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class CleanedContent:
    title: str
    text: str
    content_hash: str
    word_count: int


REMOVE_SELECTORS = (
    "script", "style", "noscript", "svg", "canvas", "iframe", "nav", "footer", "form",
    "[aria-hidden='true']", "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    ".cookie", ".cookies", ".cookie-banner", "#cookie-banner", ".newsletter", ".modal",
)


class ContentCleaner:
    def clean(self, html: str) -> CleanedContent:
        soup = BeautifulSoup(html or "", "html.parser")
        title = ""
        if soup.title:
            title = " ".join(soup.title.get_text(" ", strip=True).split())[:500]
        for selector in REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        blocks: list[str] = []
        for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "th", "td"], recursive=True):
            text = " ".join(element.get_text(" ", strip=True).split())
            if text and (not blocks or blocks[-1] != text):
                blocks.append(text)
        if not blocks:
            blocks = [main.get_text(" ", strip=True)]
        normalized = re.sub(r"\n{3,}", "\n\n", "\n".join(blocks)).strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return CleanedContent(title=title, text=normalized, content_hash=digest, word_count=len(normalized.split()))

