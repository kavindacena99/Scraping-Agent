from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from research.agent.prompts.loader import PromptTemplate

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def structured_invoke(llm, schema: type[SchemaT], prompt: PromptTemplate, **variables) -> SchemaT:
    result = llm.with_structured_output(schema).invoke(prompt.render(**variables))
    if isinstance(result, schema):
        return result
    return schema.model_validate(result)


def response_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content).strip()
    return str(content).strip()


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def evidence_text(documents: list[dict], *, include_labels: bool = True) -> tuple[str, list[dict[str, str]]]:
    sources: list[dict[str, str]] = []
    source_index: dict[str, int] = {}
    excerpts: list[str] = []
    for document in documents:
        metadata = document.get("metadata", {})
        url = str(metadata.get("source_url", ""))
        title = str(metadata.get("page_title", "") or url)
        if url not in source_index:
            source_index[url] = len(sources) + 1
            sources.append({"title": title, "url": url})
        label = f"Source {source_index[url]}" if include_labels else title
        excerpts.append(f"[{label}] {title}\nURL: {url}\n{str(document.get('content', ''))[:2200]}")
    return "\n\n".join(excerpts), sources

