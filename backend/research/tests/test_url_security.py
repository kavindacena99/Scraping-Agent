from __future__ import annotations

import socket
from unittest import TestCase
from unittest.mock import patch

from research.exceptions import BlockedURLError, InvalidURLError
from research.services.url_validator import normalize_url, same_site, validate_public_url


PUBLIC_DNS = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
]


class URLSecurityTests(TestCase):
    def test_rejects_unsupported_protocols(self):
        for url in ("file:///etc/passwd", "ftp://example.com/file", "javascript:alert(1)", "data:text/plain,x"):
            with self.subTest(url=url), self.assertRaises(InvalidURLError):
                normalize_url(url)

    def test_blocks_localhost_and_private_literal_addresses(self):
        with self.assertRaises(BlockedURLError):
            validate_public_url("http://localhost/admin")
        with self.assertRaises(BlockedURLError):
            validate_public_url("http://127.0.0.1/")
        with self.assertRaises(BlockedURLError):
            validate_public_url("http://169.254.169.254/latest/meta-data")
        with self.assertRaises(BlockedURLError):
            validate_public_url("http://[::1]/")

    @patch("research.services.url_validator.socket.getaddrinfo", return_value=PUBLIC_DNS)
    def test_accepts_and_normalizes_public_url(self, _resolve):
        result = validate_public_url("HTTPS://Example.COM:443/products/?utm_source=test#details")
        self.assertEqual(result.url, "https://example.com/products")

    @patch("research.services.url_validator.socket.getaddrinfo")
    def test_blocks_hostname_if_any_dns_answer_is_private(self, resolve):
        resolve.return_value = [
            *PUBLIC_DNS,
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 0)),
        ]
        with self.assertRaises(BlockedURLError):
            validate_public_url("https://mixed.example")

    def test_same_site_enforces_hostname_and_www_alias(self):
        self.assertTrue(same_site("https://www.example.com/products", "https://example.com"))
        self.assertFalse(same_site("https://cdn.example.com/products", "https://example.com"))
        self.assertFalse(same_site("https://evil.example/products", "https://example.com"))

    def test_query_order_fragments_and_tracking_parameters_canonicalize(self):
        first = normalize_url("https://example.com/search?b=2&utm_medium=email&a=1#results")
        second = normalize_url("https://example.com/search?a=1&b=2")
        self.assertEqual(first, second)
