from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from research.exceptions import ScrapingError
from research.models import ResearchJob
from research.services.research_runner import ResearchRunner


class ResearchAPITests(TestCase):
    def test_requires_url_and_prompt(self):
        response = self.client.post(reverse("research-create"), {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_rejects_invalid_protocol(self):
        response = self.client.post(
            reverse("research-create"),
            {"url": "file:///tmp/data", "prompt": "Find data"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("research.views.ResearchRunner.run")
    def test_creates_job_and_returns_stored_result(self, run):
        def complete(job):
            job.status = ResearchJob.Status.COMPLETED
            job.current_stage = ResearchJob.Stage.COMPLETED
            job.final_answer = "Grounded answer"
            job.sources = [{"title": "Example", "url": "https://example.com/"}]
            job.pages_scraped = 1
            job.save()
            return job

        run.side_effect = complete
        response = self.client.post(
            reverse("research-create"),
            {"url": "https://example.com", "prompt": "Find AI products"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["answer"], "Grounded answer")
        self.assertEqual(ResearchJob.objects.count(), 1)
        detail = self.client.get(reverse("research-detail", args=[response.json()["job_id"]]))
        self.assertEqual(detail.status_code, 200)

    @patch("research.views.ResearchRunner.run", side_effect=ScrapingError())
    def test_predictable_scraping_failure(self, _run):
        response = self.client.post(
            reverse("research-create"),
            {"url": "https://example.com", "prompt": "Find data"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "scraping_failed")


class RunnerFailureTests(TestCase):
    @patch("research.services.research_runner.build_research_graph")
    def test_runner_persists_failure_without_exposing_trace(self, build_graph):
        graph = MagicMock()
        graph.invoke.side_effect = RuntimeError("provider exploded")
        build_graph.return_value = graph
        job = ResearchJob.objects.create(website_url="https://example.com", user_prompt="Research it")
        with self.assertRaises(RuntimeError):
            ResearchRunner().run(job)
        job.refresh_from_db()
        self.assertEqual(job.status, ResearchJob.Status.FAILED)
        self.assertEqual(job.current_stage, ResearchJob.Stage.FAILED)
        self.assertEqual(job.error_message, "Internal research failure (RuntimeError).")
