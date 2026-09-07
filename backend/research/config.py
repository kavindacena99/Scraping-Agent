"""Typed application configuration backed by centralized Django settings."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class ProviderSettings:
    provider: str
    model: str
    api_keys: dict[str, str]


@dataclass(frozen=True)
class CrawlerSettings:
    user_agent: str
    timeout_seconds: float
    max_pages: int
    max_depth: int
    max_page_bytes: int
    max_redirects: int
    request_delay_seconds: float


@dataclass(frozen=True)
class AgentSettings:
    max_retrieval_retries: int
    max_crawl_iterations: int
    retrieval_top_k: int
    relevance_threshold: float
    chunk_size: int
    chunk_overlap: int


@dataclass(frozen=True)
class ChromaSettings:
    persist_directory: Path


def get_llm_settings() -> ProviderSettings:
    return ProviderSettings(**settings.LLM_CONFIG)


def get_embedding_settings() -> ProviderSettings:
    return ProviderSettings(**settings.EMBEDDING_CONFIG)


def get_crawler_settings() -> CrawlerSettings:
    return CrawlerSettings(**settings.CRAWLER_CONFIG)


def get_agent_settings() -> AgentSettings:
    return AgentSettings(**settings.AGENT_CONFIG)


def get_chroma_settings() -> ChromaSettings:
    return ChromaSettings(persist_directory=Path(settings.CHROMA_CONFIG["persist_directory"]))

