from __future__ import annotations

from unittest import TestCase

from research.config import CrawlerSettings
from research.services.crawler import PromptAwareCrawler, rank_links
from research.services.link_extractor import ExtractedLink
from research.services.scraper import ScrapeResult


class FakeScraper:
    def __init__(self):
        self.calls = []

    def fetch(self, url, **_kwargs):
        self.calls.append(url)
        if url.endswith("robots.txt"):
            return ScrapeResult(url, url, False, 404, "text/plain", error="HTTP 404")
        html = "<main><p>This page contains enough meaningful text for the crawler test.</p></main><a href='/products'>Products</a><a href='https://other.test/x'>External</a>"
        return ScrapeResult(url, url, True, 200, "text/html", html)

    def close(self):
        pass


def config(max_pages=2, max_depth=1):
    return CrawlerSettings("TestBot", 1, max_pages, max_depth, 10000, 1, 0)


class CrawlerTests(TestCase):
    def test_product_links_rank_above_privacy(self):
        links = [
            ExtractedLink("https://example.com/privacy", "Privacy policy"),
            ExtractedLink("https://example.com/ai-products", "AI Products"),
        ]
        ranked = rank_links(links, {"keywords": ["ai", "products"]}, 1)
        self.assertEqual(ranked[0].url, "https://example.com/ai-products")

    def test_batch_enforces_page_and_depth_limits_and_deduplicates(self):
        fake = FakeScraper()
        crawler = PromptAwareCrawler(scraper=fake, config=config(max_pages=1, max_depth=0))
        selections = [
            {"url": "https://example.com/", "depth": 0},
            {"url": "https://example.com/about", "depth": 0},
            {"url": "https://example.com/deep", "depth": 2},
        ]
        visited = set()
        pages, discovered = crawler.crawl_batch("https://example.com/", selections, {}, visited)
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(visited), 1)
        self.assertEqual(discovered, [])
