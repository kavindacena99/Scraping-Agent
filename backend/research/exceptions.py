from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import exception_handler


class ResearchError(Exception):
    code = "research_failed"
    public_message = "The website research could not be completed."
    status_code = 500

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.public_message)


class InvalidURLError(ResearchError):
    code = "invalid_url"
    public_message = "The provided website URL is invalid."
    status_code = 400


class BlockedURLError(ResearchError):
    code = "blocked_url"
    public_message = "The provided URL points to a restricted network resource."
    status_code = 400


class ScrapingError(ResearchError):
    code = "scraping_failed"
    public_message = "The website could not be analyzed."
    status_code = 502


class ProviderConfigurationError(ResearchError):
    code = "configuration_error"
    public_message = "The selected AI provider is not configured on the server."
    status_code = 503


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        if isinstance(detail, dict) and "error" in detail:
            return response
        message = "The request is invalid."
        if isinstance(detail, dict):
            first = next(iter(detail.values()), message)
            if isinstance(first, list) and first:
                message = str(first[0])
            elif isinstance(first, str):
                message = first
        return Response({"error": {"code": "validation_error", "message": message}}, status=response.status_code)
    if isinstance(exc, ResearchError):
        return Response({"error": {"code": exc.code, "message": exc.public_message}}, status=exc.status_code)
    return None

