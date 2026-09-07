from __future__ import annotations

from research.agent.state import ResearchState
from research.config import AgentSettings


def route_after_grading(state: ResearchState, config: AgentSettings) -> str:
    if state.get("evidence_sufficient", False):
        return "generate_answer"
    retries_used = max(0, state.get("retrieval_attempts_since_crawl", 1) - 1)
    if retries_used < config.max_retrieval_retries:
        return "rewrite_query"
    return "decide_more_crawling"


def route_after_crawl_decision(state: ResearchState) -> str:
    return "plan_crawl" if state.get("more_crawling_available", False) else "generate_answer"


def route_after_validation(state: ResearchState) -> str:
    validation = state.get("validation_result", {})
    if validation.get("valid", False) or state.get("answer_regeneration_count", 0) >= 2:
        return "finalize"
    return "generate_answer"
