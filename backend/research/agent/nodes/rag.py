from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from research.agent.prompts import get_prompt
from research.agent.state import ResearchState
from research.models import ResearchJob

from .context import NodeContext
from .helpers import evidence_text, json_text, structured_invoke

logger = logging.getLogger("research.agent.rag")


class RelevanceGrade(BaseModel):
    relevant: bool
    score: float = Field(ge=0, le=1)
    reason: str


class RewrittenQuery(BaseModel):
    query: str


def index_documents_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.INDEXING)
    context.vector_store.add_documents(state["job_id"], state.get("documents_to_index", []))
    return {"documents_to_index": []}


def retrieve_documents_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.RETRIEVING)
    total = state.get("retrieval_iterations", 0) + 1
    since_crawl = state.get("retrieval_attempts_since_crawl", 0) + 1
    documents = context.vector_store.search(
        state["job_id"], state["current_retrieval_query"], context.agent_config.retrieval_top_k
    )
    context.tracker.stage(ResearchJob.Stage.RETRIEVING, retrieval_iterations=total)
    logger.info("retrieval_iteration job_id=%s total=%s results=%s", state["job_id"], total, len(documents))
    return {
        "retrieved_documents": documents,
        "retrieval_iterations": total,
        "retrieval_attempts_since_crawl": since_crawl,
    }


def grade_documents_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.GRADING)
    documents = state.get("retrieved_documents", [])
    if not documents:
        return {"relevance_score": 0.0, "relevance_reason": "No evidence was retrieved.", "evidence_sufficient": False}
    evidence, _ = evidence_text(documents, include_labels=False)
    result = structured_invoke(
        context.llm,
        RelevanceGrade,
        get_prompt("relevance_grading"),
        user_query=state["user_query"],
        evidence=evidence,
    )
    sufficient = bool(result.relevant and result.score >= context.agent_config.relevance_threshold)
    return {"relevance_score": result.score, "relevance_reason": result.reason, "evidence_sufficient": sufficient}


def rewrite_query_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.REWRITING)
    result = structured_invoke(
        context.llm,
        RewrittenQuery,
        get_prompt("query_rewriting"),
        user_query=state["user_query"],
        current_query=state["current_retrieval_query"],
        research_intent=json_text(state["research_intent"]),
        grade_reason=state.get("relevance_reason", "Evidence was insufficient."),
    )
    query = result.query.strip() or state["current_retrieval_query"]
    return {"current_retrieval_query": query}

