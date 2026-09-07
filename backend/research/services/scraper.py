"""Bounded HTTP scraper with validation on the initial URL and every redirect."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

from research.config import CrawlerSettings, get_crawler_settings
from research.exceptions import BlockedURLError, InvalidURLError

from .url_validator import same_site, validate_public_url

logger = logging.getLogger("research.scraper")


@dataclass(frozen=True)
class ScrapeResult:
    requested_url: str
    final_url: str = ""
    ok: bool = False
    status_code: int | None = None
    content_type: str = ""
    body: str = ""
    error: str = ""
    redirect_chain: tuple[str, ...] = field(default_factory=tuple)


class HttpScraper:
    ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")

    def __init__(self, config: CrawlerSettings | None = None, client: httpx.Client | None = None) -> None:
        self.config = config or get_crawler_settings()
        self._owns_client = client is None
        self.client = client or httpx.Client(
            follow_redirects=False,
            timeout=self.config.timeout_seconds,
            trust_env=False,
            headers={"User-Agent": self.config.user_agent, "Accept": "text/html,text/plain;q=0.9"},
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch(self, url: str, *, allowed_root_url: str | None = None) -> ScrapeResult:
        requested_url = url
        redirects: list[str] = []
        try:
            current = validate_public_url(url).url
            if allowed_root_url and not same_site(current, allowed_root_url):
                return ScrapeResult(requested_url, current, False, error="URL left the allowed website.")
            for _ in range(self.config.max_redirects + 1):
                logger.info("page_scraping_started url=%s", current)
                with self.client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            return ScrapeResult(requested_url, current, False, response.status_code, error="Redirect has no destination.")
                        destination = validate_public_url(urljoin(current, location)).url
                        if allowed_root_url and not same_site(destination, allowed_root_url):
                            return ScrapeResult(
                                requested_url,
                                current,
                                False,
                                response.status_code,
                                error="Redirect left the allowed website.",
                                redirect_chain=tuple(redirects),
                            )
                        redirects.append(destination)
                        current = destination
                        continue
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if not any(content_type == allowed for allowed in self.ALLOWED_CONTENT_TYPES):
                        return ScrapeResult(requested_url, current, False, response.status_code, content_type, error="Unsupported content type.", redirect_chain=tuple(redirects))
                    if response.status_code >= 400:
                        return ScrapeResult(requested_url, current, False, response.status_code, content_type, error=f"HTTP {response.status_code}.", redirect_chain=tuple(redirects))
                    declared_size = int(response.headers.get("content-length", "0") or 0)
                    if declared_size > self.config.max_page_bytes:
                        return ScrapeResult(requested_url, current, False, response.status_code, content_type, error="Response is too large.", redirect_chain=tuple(redirects))
                    payload = bytearray()
                    for chunk in response.iter_bytes():
                        payload.extend(chunk)
                        if len(payload) > self.config.max_page_bytes:
                            return ScrapeResult(requested_url, current, False, response.status_code, content_type, error="Response is too large.", redirect_chain=tuple(redirects))
                    encoding = response.encoding or "utf-8"
                    body = bytes(payload).decode(encoding, errors="replace")
                    return ScrapeResult(requested_url, current, True, response.status_code, content_type, body, redirect_chain=tuple(redirects))
            return ScrapeResult(requested_url, current, False, error="Too many redirects.", redirect_chain=tuple(redirects))
        except (BlockedURLError, InvalidURLError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
            logger.warning("page_scraping_failed url=%s error=%s", requested_url, type(exc).__name__)
            return ScrapeResult(requested_url, error=f"Network error: {type(exc).__name__}.")
        except (LookupError, ValueError) as exc:
            return ScrapeResult(requested_url, error=f"Invalid response: {type(exc).__name__}.")
