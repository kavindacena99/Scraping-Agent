from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .loader import PromptTemplate, PromptTemplateError, load_prompt

PROMPT_DIRECTORY = Path(__file__).resolve().parent
REGISTERED_PROMPTS = {
    "intent_analysis": "intent_analysis.yaml",
    "crawl_planning": "crawl_planning.yaml",
    "relevance_grading": "relevance_grading.yaml",
    "query_rewriting": "query_rewriting.yaml",
    "answer_generation": "answer_generation.yaml",
    "answer_validation": "answer_validation.yaml",
}


@lru_cache(maxsize=None)
def get_prompt(name: str) -> PromptTemplate:
    filename = REGISTERED_PROMPTS.get(name)
    if not filename:
        raise PromptTemplateError(f"Unknown prompt template: {name}.")
    prompt = load_prompt(PROMPT_DIRECTORY / filename)
    if prompt.name != name:
        raise PromptTemplateError(f"Prompt registry name '{name}' does not match template name '{prompt.name}'.")
    return prompt

