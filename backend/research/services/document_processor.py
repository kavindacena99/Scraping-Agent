from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from research.config import AgentSettings, get_agent_settings

from .content_cleaner import ContentCleaner


class DocumentProcessor:
    MIN_WORDS = 25

    def __init__(self, config: AgentSettings | None = None) -> None:
        self.config = config or get_agent_settings()
        if self.config.chunk_overlap >= self.config.chunk_size:
            raise ValueError("DOCUMENT_CHUNK_OVERLAP must be smaller than DOCUMENT_CHUNK_SIZE.")
        self.cleaner = ContentCleaner()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def process(
        self, pages: list[dict], job_id: str, existing_hashes: set[str] | None = None
    ) -> tuple[list[Document], list[dict]]:
        chunks: list[Document] = []
        page_metadata: list[dict] = []
        seen_hashes: set[str] = set(existing_hashes or set())
        for page in pages:
            if not page.get("ok"):
                page_metadata.append({**page, "title": "", "content_hash": "", "word_count": 0})
                continue
            cleaned = self.cleaner.clean(page.get("html", ""))
            info = {**page, "title": cleaned.title, "content_hash": cleaned.content_hash, "word_count": cleaned.word_count}
            page_metadata.append(info)
            if cleaned.word_count < self.MIN_WORDS or cleaned.content_hash in seen_hashes:
                continue
            seen_hashes.add(cleaned.content_hash)
            source_metadata = {
                "job_id": job_id,
                "source_url": page["url"],
                "page_title": cleaned.title,
                "content_hash": cleaned.content_hash,
            }
            split_documents = self.splitter.create_documents([cleaned.text], metadatas=[source_metadata])
            for index, document in enumerate(split_documents):
                document.metadata["chunk_index"] = index
                chunks.append(document)
        return chunks, page_metadata
