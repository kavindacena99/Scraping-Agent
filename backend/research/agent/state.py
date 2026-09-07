from __future__ import annotations

from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    job_id: str
    root_url: str
    validated_url: str
    user_query: str
    research_intent: dict[str, Any]
    crawl_candidates: list[dict[str, Any]]
    selected_urls: list[dict[str, Any]]
    visited_urls: list[str]
    new_scraped_pages: list[dict[str, Any]]
    scraped_pages: list[dict[str, Any]]
    documents_to_index: list[Any]
    indexed_content_hashes: list[str]
    retrieved_documents: list[dict[str, Any]]
    original_retrieval_query: str
    current_retrieval_query: str
    relevance_score: float
    relevance_reason: str
    evidence_sufficient: bool
    more_crawling_available: bool
    retrieval_iterations: int
    retrieval_attempts_since_crawl: int
    crawl_iterations: int
    answer_regeneration_count: int
    final_answer: str
    sources: list[dict[str, str]]
    validation_result: dict[str, Any]
    error: str
