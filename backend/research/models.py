from __future__ import annotations

import hashlib
import uuid

from django.db import models


class ResearchJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Stage(models.TextChoices):
        VALIDATING_URL = "validating_url", "Validating URL"
        ANALYZING_REQUEST = "analyzing_request", "Analyzing request"
        PLANNING_CRAWL = "planning_crawl", "Planning crawl"
        SCRAPING = "scraping", "Scraping"
        PROCESSING = "processing_documents", "Processing documents"
        INDEXING = "indexing", "Indexing"
        RETRIEVING = "retrieving", "Retrieving"
        GRADING = "grading", "Grading"
        REWRITING = "rewriting_query", "Rewriting query"
        ADDITIONAL_CRAWLING = "additional_crawling", "Additional crawling"
        GENERATING = "generating_answer", "Generating answer"
        VALIDATING_ANSWER = "validating_answer", "Validating answer"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    website_url = models.URLField(max_length=2048)
    user_prompt = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    current_stage = models.CharField(max_length=40, choices=Stage.choices, default=Stage.VALIDATING_URL)
    final_answer = models.TextField(blank=True)
    sources = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    pages_scraped = models.PositiveIntegerField(default=0)
    retrieval_iterations = models.PositiveIntegerField(default=0)
    crawl_iterations = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.uuid} - {self.status}"


class ScrapedPage(models.Model):
    class ScrapeStatus(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    research_job = models.ForeignKey(ResearchJob, on_delete=models.CASCADE, related_name="scraped_pages")
    url = models.URLField(max_length=2048)
    url_hash = models.CharField(max_length=64, editable=False, db_index=True)
    title = models.CharField(max_length=500, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    scrape_status = models.CharField(max_length=20, choices=ScrapeStatus.choices)
    error_message = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    word_count = models.PositiveIntegerField(default=0)
    depth = models.PositiveSmallIntegerField(default=0)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scraped_at"]
        constraints = [
            models.UniqueConstraint(fields=["research_job", "url_hash"], name="unique_scraped_url_per_job")
        ]

    def save(self, *args, **kwargs):
        self.url_hash = hashlib.sha256(self.url.encode("utf-8")).hexdigest()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.url
