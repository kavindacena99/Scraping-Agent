from __future__ import annotations

import socket
from unittest import TestCase
from unittest.mock import MagicMock, patch

from research.config import CrawlerSettings
from research.exceptions import BlockedURLError
from research.services.content_cleaner import ContentCleaner
from research.services.link_extractor import LinkExtractor
from research.services.scraper import HttpScraper


def crawler_config(**overrides):
    values = {
        "user_agent": "TestBot/1.0",
        "timeout_seconds": 1,
        "max_pages": 3,
        "max_depth": 1,
        "max_page_bytes": 1000,
        "max_redirects": 2,
        "request_delay_seconds": 0,
    }
    values.update(overrides)
    return CrawlerSettings(**values)


class FakeResponse:
    def __init__(self, status_code, headers, body=b""):
        self.status_code = status_code
        self.headers = headers
        self._body = body
        self.encoding = "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_bytes(self):
        yield self._body


class ScrapingTests(TestCase):
    def test_cleaner_removes_navigation_scripts_and_duplicate_blocks(self):
        html = """<html><head><title> Demo </title><script>secret()</script></head><body>
        <nav>Menu Item</nav><main><h1>AI Platform</h1><p>Useful product details are provided here for customers.</p>
        <p>Useful product details are provided here for customers.</p><ul><li>Feature one</li></ul></main><footer>Legal</footer></body></html>"""
        result = ContentCleaner().clean(html)
        self.assertIn("AI Platform", result.text)
        self.assertIn("Feature one", result.text)
        self.assertNotIn("Menu Item", result.text)
        self.assertNotIn("secret", result.text)
        self.assertEqual(result.text.count("Useful product"), 1)

    def test_link_extractor_keeps_only_unique_internal_html_links(self):
        html = """<a href='/products#top'>Products</a><a href='https://example.com/products'>Again</a>
        <a href='https://external.test/x'>External</a><a href='http://localhost/admin'>Blocked</a><a href='/image.png'>Image</a>"""
        links = LinkExtractor().extract_internal(html, "https://example.com/", "https://example.com/")
        self.assertEqual([link.url for link in links], ["https://example.com/products"])

    @patch("research.services.url_validator.socket.getaddrinfo")
    def test_redirect_destination_is_revalidated(self, resolve):
        resolve.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        client = MagicMock()
        client.stream.return_value = FakeResponse(302, {"location": "http://127.0.0.1/admin"})
        scraper = HttpScraper(crawler_config(), client=client)
        with self.assertRaises(BlockedURLError):
            scraper.fetch("https://example.com/", allowed_root_url="https://example.com/")

    @patch("research.services.url_validator.socket.getaddrinfo")
    def test_response_size_limit_applies_while_streaming(self, resolve):
        resolve.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        client = MagicMock()
        client.stream.return_value = FakeResponse(200, {"content-type": "text/html"}, b"x" * 1001)
        result = HttpScraper(crawler_config(), client=client).fetch("https://example.com/")
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Response is too large.")

    @patch("research.services.url_validator.socket.getaddrinfo")
    def test_external_redirect_is_rejected_before_following(self, resolve):
        resolve.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        client = MagicMock()
        client.stream.return_value = FakeResponse(302, {"location": "https://external.test/landing"})
        result = HttpScraper(crawler_config(), client=client).fetch(
            "https://example.com/", allowed_root_url="https://example.com/"
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Redirect left the allowed website.")
        self.assertEqual(client.stream.call_count, 1)
