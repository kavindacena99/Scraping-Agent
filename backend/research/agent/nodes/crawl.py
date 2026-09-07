from __future__ import annotations

import hashlib
import logging

from pydantic import BaseModel, Field

from research.agent.prompts import get_prompt
from research.agent.state import ResearchState
from research.exceptions import ScrapingError
from research.models import ResearchJob, ScrapedPage
from research.services.crawler import PromptAwareCrawler
from research.services.document_processor import DocumentProcessor
from research.services.url_validator import validate_public_url

from .context import NodeContext
from .helpers import json_text, structured_invoke

logger = logging.getLogger("research.agent.crawl")


class IntentResult(BaseModel):
    intent: str
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    preferred_page_types: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


class CrawlChoice(BaseModel):
    url: str
    reason: str = ""


class CrawlPlan(BaseModel):
    selections: list[CrawlChoice] = Field(default_factory=list)


def validate_url_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.VALIDATING_URL)
    validated = validate_public_url(state["root_url"])
    return {"validated_url": validated.url, "root_url": validated.url}


def analyze_request_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.ANALYZING_REQUEST)
    result = structured_invoke(
        context.llm,
        IntentResult,
        get_prompt("intent_analysis"),
        website_url=state["validated_url"],
        user_query=state["user_query"],
    )
    intent = result.model_dump()
    first_query = next((query.strip() for query in result.search_queries if query.strip()), state["user_query"])
    return {
        "research_intent": intent,
        "original_retrieval_query": state["user_query"],
        "current_retrieval_query": first_query,
    }


def plan_crawl_node(state: ResearchState, context: NodeContext) -> dict:
    candidates = [item for item in state.get("crawl_candidates", []) if item["url"] not in set(state.get("visited_urls", []))]
    if not candidates:
        context.tracker.stage(ResearchJob.Stage.PLANNING_CRAWL)
        return {"selected_urls": [{"url": state["validated_url"], "depth": 0, "score": 100.0}]}

    context.tracker.stage(ResearchJob.Stage.ADDITIONAL_CRAWLING)
    remaining_capacity = context.crawler_config.max_pages - len(state.get("visited_urls", []))
    max_selections = max(0, min(remaining_capacity, 3))
    shortlist = candidates[: max(8, max_selections)]
    if max_selections == 0:
        return {"selected_urls": []}
    allowed = {item["url"]: item for item in shortlist}
    try:
        result = structured_invoke(
            context.llm,
            CrawlPlan,
            get_prompt("crawl_planning"),
            research_intent=json_text(state["research_intent"]),
            candidate_links=json_text(shortlist),
            max_selections=max_selections,
        )
        chosen_urls = [choice.url for choice in result.selections if choice.url in allowed]
    except Exception as exc:
        logger.warning("crawl_planner_fallback error=%s", type(exc).__name__)
        chosen_urls = []
    chosen_urls.extend(item["url"] for item in shortlist if item["url"] not in chosen_urls)
    selected = [allowed[url] for url in dict.fromkeys(chosen_urls) if url in allowed][:max_selections]
    return {"selected_urls": selected}


def scrape_pages_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.SCRAPING)
    crawler = PromptAwareCrawler(config=context.crawler_config)
    visited = set(state.get("visited_urls", []))
    try:
        pages, discovered = crawler.crawl_batch(
            state["validated_url"], state.get("selected_urls", []), state["research_intent"], visited
        )
    finally:
        crawler.scraper.close()
    all_pages = [*state.get("scraped_pages", []), *pages]
    existing_candidates = {
        item["url"]: item
        for item in state.get("crawl_candidates", [])
        if item["url"] not in visited
    }
    for candidate in discovered:
        existing_candidates[candidate["url"]] = candidate
    successful = [page for page in all_pages if page.get("ok")]
    if not successful:
        raise ScrapingError()
    crawl_iterations = state.get("crawl_iterations", 0) + 1
    context.tracker.stage(
        ResearchJob.Stage.SCRAPING,
        pages_scraped=len(successful),
        crawl_iterations=crawl_iterations,
    )
    return {
        "new_scraped_pages": pages,
        "scraped_pages": all_pages,
        "visited_urls": sorted(visited),
        "crawl_candidates": sorted(existing_candidates.values(), key=lambda item: (-item["score"], item["url"])),
        "crawl_iterations": crawl_iterations,
        "retrieval_attempts_since_crawl": 0,
    }


def process_documents_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.PROCESSING)
    processor = DocumentProcessor(context.agent_config)
    existing_hashes = set(state.get("indexed_content_hashes", []))
    documents, page_metadata = processor.process(
        state.get("new_scraped_pages", []), state["job_id"], existing_hashes
    )
    for page in page_metadata:
        scrape_status = ScrapedPage.ScrapeStatus.SUCCESS
        if not page.get("ok"):
            scrape_status = (
                ScrapedPage.ScrapeStatus.SKIPPED
                if "robots.txt" in str(page.get("error", ""))
                else ScrapedPage.ScrapeStatus.FAILED
            )
        ScrapedPage.objects.update_or_create(
            research_job=context.job,
            url_hash=hashlib.sha256(page["url"].encode("utf-8")).hexdigest(),
            defaults={
                "url": page["url"],
                "title": page.get("title", ""),
                "status_code": page.get("status_code"),
                "content_hash": page.get("content_hash", ""),
                "scrape_status": scrape_status,
                "error_message": str(page.get("error", ""))[:500],
                "content_type": page.get("content_type", "")[:100],
                "word_count": page.get("word_count", 0),
                "depth": page.get("depth", 0),
            },
        )
    indexed_hashes = existing_hashes | {document.metadata["content_hash"] for document in documents}
    return {"documents_to_index": documents, "indexed_content_hashes": sorted(indexed_hashes)}


def decide_more_crawling_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.ADDITIONAL_CRAWLING)
    visited = set(state.get("visited_urls", []))
    unvisited = any(item["url"] not in visited for item in state.get("crawl_candidates", []))
    additional_crawls_used = max(0, state.get("crawl_iterations", 1) - 1)
    has_page_capacity = len(visited) < context.crawler_config.max_pages
    return {
        "more_crawling_available": bool(
            unvisited
            and has_page_capacity
            and additional_crawls_used < context.agent_config.max_crawl_iterations
        )
    }
