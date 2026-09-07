from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document

from research.config import ChromaSettings, get_chroma_settings


def collection_name(job_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", job_id.replace("-", "_"))
    return f"research_{cleaned}"[:63]


class JobVectorStore:
    """Uses one collection per job, making cross-job retrieval impossible by design."""

    def __init__(self, embedding_model, config: ChromaSettings | None = None) -> None:
        self.embedding_model = embedding_model
        self.config = config or get_chroma_settings()
        Path(self.config.persist_directory).mkdir(parents=True, exist_ok=True)

    def _store(self, job_id: str):
        # Import lazily so configuration checks and mocked tests do not require
        # Chroma's native runtime before retrieval is actually used.
        from langchain_chroma import Chroma

        return Chroma(
            collection_name=collection_name(job_id),
            embedding_function=self.embedding_model,
            persist_directory=str(self.config.persist_directory),
        )

    def add_documents(self, job_id: str, documents: list[Document]) -> None:
        if not documents:
            return
        if any(document.metadata.get("job_id") != job_id for document in documents):
            raise ValueError("All documents must belong to the requested job.")
        ids = [f"{document.metadata['content_hash']}:{document.metadata['chunk_index']}" for document in documents]
        self._store(job_id).add_documents(documents, ids=ids)

    def search(self, job_id: str, query: str, k: int) -> list[dict]:
        results = self._store(job_id).similarity_search_with_relevance_scores(query, k=k)
        return [
            {"content": document.page_content, "metadata": document.metadata, "similarity": float(score)}
            for document, score in results
            if document.metadata.get("job_id") == job_id
        ]

    def delete_job(self, job_id: str) -> None:
        self._store(job_id).delete_collection()
