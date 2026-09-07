from __future__ import annotations

import re
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from research.config import CrawlerSettings, get_crawler_settings

from .link_extractor import ExtractedLink, LinkExtractor
from .scraper import HttpScraper, ScrapeResult
from .url_validator import normalize_url, same_site

LOW_VALUE_TERMS = {"privacy", "terms", "cookie", "login", "signup", "contact", "careers", "press", "legal"}
HIGH_VALUE_TERMS = {"product", "products", "platform", "solution", "solutions", "service", "services", "technology", "features", "industries", "about", "ai"}


@dataclass(frozen=True)
class CrawlCandidate:
    url: str
    anchor_text: str
    depth: int
    score: float


class RobotsPolicy:
    def __init__(self, scraper: HttpScraper, root_url: str, user_agent: str) -> None:
        self.user_agent = user_agent
        self.parser = urllib.robotparser.RobotFileParser()
        robots_url = urljoin(root_url, "/robots.txt")
        result = scraper.fetch(robots_url, allowed_root_url=root_url)
        if result.ok:
            self.parser.set_url(robots_url)
            self.parser.parse(result.body.splitlines())
            self.available = True
        else:
            self.available = False

    def allowed(self, url: str) -> bool:
        return not self.available or self.parser.can_fetch(self.user_agent, url)


def score_link(link: ExtractedLink, intent: dict) -> float:
    path = urlsplit(link.url).path.lower()
    haystack = f"{path} {link.anchor_text.lower()}"
    terms = set(re.findall(r"[a-z0-9]+", haystack))
    wanted = {
        str(term).lower()
        for key in ("topics", "keywords", "preferred_page_types")
        for term in intent.get(key, [])
    }
    score = 1.0 + min(path.count("/"), 5) * -0.08
    score += 1.5 * len(terms & wanted)
    score += 0.8 * len(terms & HIGH_VALUE_TERMS)
    score -= 2.0 * len(terms & LOW_VALUE_TERMS)
    if urlsplit(link.url).query:
        score -= 0.25
    return round(score, 3)


def rank_links(links: list[ExtractedLink], intent: dict, depth: int) -> list[CrawlCandidate]:
    candidates = [CrawlCandidate(link.url, link.anchor_text, depth, score_link(link, intent)) for link in links]
    return sorted(candidates, key=lambda item: (-item.score, item.url))


class PromptAwareCrawler:
    """Fetches an explicit bounded batch and returns ranked newly discovered links."""

    def __init__(self, scraper: HttpScraper | None = None, config: CrawlerSettings | None = None) -> None:
        self.config = config or get_crawler_settings()
        self.scraper = scraper or HttpScraper(self.config)
        self.link_extractor = LinkExtractor()

    def crawl_batch(
        self,
        root_url: str,
        selections: list[dict],
        intent: dict,
        visited: set[str],
    ) -> tuple[list[dict], list[dict]]:
        root_url = normalize_url(root_url)
        robots = RobotsPolicy(self.scraper, root_url, self.config.user_agent)
        pages: list[dict] = []
        discovered: dict[str, dict] = {}
        for selection in selections[: self.config.max_pages - len(visited)]:
            url = normalize_url(selection["url"])
            depth = int(selection.get("depth", 0))
            if url in visited or depth > self.config.max_depth or not same_site(url, root_url):
                continue
            if not robots.allowed(url):
                pages.append({"url": url, "depth": depth, "ok": False, "error": "Blocked by robots.txt."})
                visited.add(url)
                continue
            if pages and self.config.request_delay_seconds:
                time.sleep(self.config.request_delay_seconds)
            result: ScrapeResult = self.scraper.fetch(url, allowed_root_url=root_url)
            visited.add(url)
            if result.final_url:
                visited.add(normalize_url(result.final_url))
            page = {
                "url": result.final_url or url,
                "requested_url": url,
                "depth": depth,
                "ok": result.ok,
                "status_code": result.status_code,
                "content_type": result.content_type,
                "html": result.body,
                "error": result.error,
            }
            pages.append(page)
            if result.ok and depth < self.config.max_depth:
                links = self.link_extractor.extract_internal(result.body, result.final_url or url, root_url)
                for candidate in rank_links(links, intent, depth + 1):
                    if candidate.url not in visited:
                        discovered[candidate.url] = candidate.__dict__
        return pages, sorted(discovered.values(), key=lambda item: (-item["score"], item["url"]))
