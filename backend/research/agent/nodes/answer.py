from __future__ import annotations

from pydantic import BaseModel, Field

from research.agent.prompts import get_prompt
from research.agent.state import ResearchState
from research.models import ResearchJob

from .context import NodeContext
from .helpers import evidence_text, response_text, structured_invoke


class AnswerValidation(BaseModel):
    valid: bool
    grounded: bool
    addresses_question: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    reason: str


def generate_answer_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.GENERATING)
    documents = state.get("retrieved_documents", [])
    evidence, sources = evidence_text(documents)
    if not evidence:
        return {
            "final_answer": "The requested information could not be found on the analyzed pages.",
            "sources": [],
            "answer_regeneration_count": state.get("answer_regeneration_count", 0) + 1,
        }
    stricter = state.get("answer_regeneration_count", 0) > 0
    grounding = (
        "This is a regeneration after a failed grounding check. Remove every claim that is not directly supported."
        if stricter
        else "Every factual claim must be traceable to an evidence excerpt."
    )
    response = context.llm.invoke(
        get_prompt("answer_generation").render(
            user_query=state["user_query"], evidence=evidence, grounding_instruction=grounding
        )
    )
    return {
        "final_answer": response_text(response),
        "sources": sources,
        "answer_regeneration_count": state.get("answer_regeneration_count", 0) + 1,
    }


def validate_answer_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.VALIDATING_ANSWER)
    documents = state.get("retrieved_documents", [])
    if not documents:
        return {"validation_result": {"valid": True, "grounded": True, "addresses_question": True, "reason": "The answer reports an evidence gap."}}
    evidence, _ = evidence_text(documents)
    result = structured_invoke(
        context.llm,
        AnswerValidation,
        get_prompt("answer_validation"),
        user_query=state["user_query"],
        answer=state["final_answer"],
        evidence=evidence,
    )
    return {"validation_result": result.model_dump()}


def finalize_node(state: ResearchState, context: NodeContext) -> dict:
    context.tracker.stage(ResearchJob.Stage.COMPLETED)
    return {}

