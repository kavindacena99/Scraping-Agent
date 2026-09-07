"""URL normalization and SSRF defenses used before every outbound request."""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from research.exceptions import BlockedURLError, InvalidURLError

SUPPORTED_SCHEMES = {"http", "https"}
BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".corp")
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


@dataclass(frozen=True)
class ValidatedURL:
    url: str
    hostname: str
    resolved_ips: tuple[str, ...]


def _is_restricted_ip(value: str) -> bool:
    address = ipaddress.ip_address(value.split("%", 1)[0])
    # is_global excludes private, loopback, link-local, multicast, reserved,
    # unspecified, documentation, and other non-public address ranges.
    return not address.is_global


def resolve_public_ips(hostname: str) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InvalidURLError("The hostname could not be resolved.") from exc
    addresses = tuple(sorted({record[4][0] for record in records}))
    if not addresses:
        raise InvalidURLError("The hostname did not resolve to an address.")
    if any(_is_restricted_ip(address) for address in addresses):
        raise BlockedURLError()
    return addresses


def normalize_url(url: str, *, drop_fragment: bool = True) -> str:
    raw = (url or "").strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise InvalidURLError() from exc
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES or not parsed.hostname:
        raise InvalidURLError()
    if parsed.username or parsed.password:
        raise InvalidURLError("Embedded credentials are not allowed.")
    hostname = parsed.hostname.rstrip(".").lower()
    if not hostname or hostname == "localhost" or hostname.endswith(BLOCKED_HOST_SUFFIXES):
        raise BlockedURLError()
    try:
        hostname_ascii = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise InvalidURLError() from exc
    if "%" in hostname_ascii:
        raise BlockedURLError()
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    formatted_host = f"[{hostname_ascii}]" if ":" in hostname_ascii else hostname_ascii
    netloc = formatted_host if not port or default_port else f"{formatted_host}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    clean_query = sorted([
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ])
    return urlunsplit((scheme, netloc, path, urlencode(clean_query, doseq=True), "" if drop_fragment else parsed.fragment))


def validate_public_url(url: str) -> ValidatedURL:
    normalized = normalize_url(url)
    hostname = urlsplit(normalized).hostname
    assert hostname is not None
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        ips = resolve_public_ips(hostname)
    else:
        if _is_restricted_ip(str(literal)):
            raise BlockedURLError()
        ips = (str(literal),)
    return ValidatedURL(url=normalized, hostname=hostname, resolved_ips=ips)


def same_site(url: str, root_url: str) -> bool:
    """Allow only the root hostname (treating the common www alias as equal)."""
    try:
        candidate = (urlsplit(normalize_url(url)).hostname or "").removeprefix("www.")
        root = (urlsplit(normalize_url(root_url)).hostname or "").removeprefix("www.")
    except (InvalidURLError, BlockedURLError):
        return False
    return bool(candidate and candidate == root)
