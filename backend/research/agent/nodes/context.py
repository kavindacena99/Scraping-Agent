from __future__ import annotations

import logging
from functools import cached_property

from research.agent.providers import get_embedding_model, get_llm
from research.config import AgentSettings, CrawlerSettings, get_agent_settings, get_crawler_settings
from research.models import ResearchJob
from research.services.vector_store import JobVectorStore

logger = logging.getLogger("research.agent")


class JobTracker:
    def __init__(self, job: ResearchJob) -> None:
        self.job = job

    def stage(self, stage: str, **metrics: int) -> None:
        updates = {"current_stage": stage, **metrics}
        ResearchJob.objects.filter(pk=self.job.pk).update(**updates)
        for key, value in updates.items():
            setattr(self.job, key, value)


class NodeContext:
    def __init__(
        self,
        job: ResearchJob,
        *,
        llm=None,
        embedding_model=None,
        vector_store=None,
        agent_config: AgentSettings | None = None,
        crawler_config: CrawlerSettings | None = None,
    ) -> None:
        self.job = job
        self.tracker = JobTracker(job)
        self._llm = llm
        self._embedding_model = embedding_model
        self._vector_store = vector_store
        self.agent_config = agent_config or get_agent_settings()
        self.crawler_config = crawler_config or get_crawler_settings()

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = JobVectorStore(self.embedding_model)
        return self._vector_store

