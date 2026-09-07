from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from langchain_core.documents import Document

from research.agent.routing.conditions import route_after_crawl_decision, route_after_grading, route_after_validation
from research.config import AgentSettings, ChromaSettings
from research.services.vector_store import JobVectorStore, collection_name


CONFIG = AgentSettings(2, 1, 5, 0.65, 1000, 100)


class RoutingTests(TestCase):
    def test_good_evidence_routes_to_answer(self):
        self.assertEqual(route_after_grading({"evidence_sufficient": True}, CONFIG), "generate_answer")

    def test_retry_limit_routes_to_explicit_crawl_decision(self):
        state = {
            "evidence_sufficient": False,
            "retrieval_attempts_since_crawl": 3,
            "crawl_iterations": 1,
            "visited_urls": ["https://example.com/"],
            "crawl_candidates": [{"url": "https://example.com/products"}],
        }
        self.assertEqual(route_after_grading(state, CONFIG), "decide_more_crawling")
        self.assertEqual(route_after_crawl_decision({"more_crawling_available": True}), "plan_crawl")
        self.assertEqual(route_after_crawl_decision({"more_crawling_available": False}), "generate_answer")

    def test_answer_regeneration_is_bounded(self):
        self.assertEqual(route_after_validation({"validation_result": {"valid": False}, "answer_regeneration_count": 1}), "generate_answer")
        self.assertEqual(route_after_validation({"validation_result": {"valid": False}, "answer_regeneration_count": 2}), "finalize")


class FakeChroma:
    def __init__(self, documents=None):
        self.documents = documents or []
        self.added = []
        self.deleted = False

    def add_documents(self, documents, ids):
        self.added.extend(documents)

    def similarity_search_with_relevance_scores(self, query, k):
        return [(document, 0.9) for document in self.documents[:k]]

    def delete_collection(self):
        self.deleted = True


class VectorIsolationTests(TestCase):
    def test_collection_name_is_job_specific(self):
        self.assertNotEqual(collection_name("job-a"), collection_name("job-b"))

    def test_rejects_cross_job_documents_on_index(self):
        store = JobVectorStore(MagicMock(), ChromaSettings(PathForTest()))
        store._store = lambda job_id: FakeChroma()  # type: ignore[method-assign]
        document = Document(page_content="text", metadata={"job_id": "other", "content_hash": "a", "chunk_index": 0})
        with self.assertRaisesRegex(ValueError, "belong"):
            store.add_documents("expected", [document])

    def test_filters_cross_job_results_defensively(self):
        matching = Document(page_content="right", metadata={"job_id": "job-a", "source_url": "https://a.test"})
        foreign = Document(page_content="wrong", metadata={"job_id": "job-b", "source_url": "https://b.test"})
        store = JobVectorStore(MagicMock(), ChromaSettings(PathForTest()))
        store._store = lambda job_id: FakeChroma([matching, foreign])  # type: ignore[method-assign]
        results = store.search("job-a", "query", 5)
        self.assertEqual([item["content"] for item in results], ["right"])


def PathForTest():
    from pathlib import Path
    from tempfile import gettempdir

    return Path(gettempdir()) / "research-vector-test"
