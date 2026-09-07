from __future__ import annotations

import logging

from django.utils import timezone

from research.agent.graph import build_research_graph
from research.agent.nodes.context import NodeContext
from research.exceptions import ResearchError
from research.models import ResearchJob

logger = logging.getLogger("research.runner")


class ResearchRunner:
    """Synchronous orchestration boundary that can later move behind a task queue."""

    def __init__(self, *, context_factory=NodeContext) -> None:
        self.context_factory = context_factory

    def run(self, job: ResearchJob) -> ResearchJob:
        job.status = ResearchJob.Status.RUNNING
        job.started_at = timezone.now()
        job.error_message = ""
        job.save(update_fields=["status", "started_at", "error_message"])
        logger.info("job_started job_id=%s", job.uuid)
        try:
            context = self.context_factory(job)
            graph = build_research_graph(context)
            result = graph.invoke(
                {
                    "job_id": str(job.uuid),
                    "root_url": job.website_url,
                    "user_query": job.user_prompt,
                    "crawl_candidates": [],
                    "selected_urls": [],
                    "visited_urls": [],
                    "scraped_pages": [],
                    "indexed_content_hashes": [],
                    "retrieved_documents": [],
                    "retrieval_iterations": 0,
                    "retrieval_attempts_since_crawl": 0,
                    "crawl_iterations": 0,
                    "answer_regeneration_count": 0,
                },
                config={"recursion_limit": 50},
            )
            job.status = ResearchJob.Status.COMPLETED
            job.current_stage = ResearchJob.Stage.COMPLETED
            job.final_answer = result.get("final_answer", "")
            job.sources = result.get("sources", [])
            job.pages_scraped = len([page for page in result.get("scraped_pages", []) if page.get("ok")])
            job.retrieval_iterations = result.get("retrieval_iterations", 0)
            job.crawl_iterations = result.get("crawl_iterations", 0)
            job.completed_at = timezone.now()
            job.save()
            logger.info("job_completed job_id=%s pages=%s", job.uuid, job.pages_scraped)
            return job
        except Exception as exc:
            job.status = ResearchJob.Status.FAILED
            job.current_stage = ResearchJob.Stage.FAILED
            job.error_message = (
                exc.public_message
                if isinstance(exc, ResearchError)
                else f"Internal research failure ({type(exc).__name__})."
            )
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "current_stage", "error_message", "completed_at"])
            logger.error("job_failed job_id=%s error_type=%s", job.uuid, type(exc).__name__)
            raise
