import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="ResearchJob",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("website_url", models.URLField(max_length=2048)),
                ("user_prompt", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("current_stage", models.CharField(choices=[("validating_url", "Validating URL"), ("analyzing_request", "Analyzing request"), ("planning_crawl", "Planning crawl"), ("scraping", "Scraping"), ("processing_documents", "Processing documents"), ("indexing", "Indexing"), ("retrieving", "Retrieving"), ("grading", "Grading"), ("rewriting_query", "Rewriting query"), ("additional_crawling", "Additional crawling"), ("generating_answer", "Generating answer"), ("validating_answer", "Validating answer"), ("completed", "Completed"), ("failed", "Failed")], default="validating_url", max_length=40)),
                ("final_answer", models.TextField(blank=True)),
                ("sources", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("pages_scraped", models.PositiveIntegerField(default=0)),
                ("retrieval_iterations", models.PositiveIntegerField(default=0)),
                ("crawl_iterations", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ScrapedPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.URLField(max_length=2048)),
                ("url_hash", models.CharField(db_index=True, editable=False, max_length=64)),
                ("title", models.CharField(blank=True, max_length=500)),
                ("status_code", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("content_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("scrape_status", models.CharField(choices=[("success", "Success"), ("failed", "Failed"), ("skipped", "Skipped")], max_length=20)),
                ("error_message", models.CharField(blank=True, max_length=500)),
                ("content_type", models.CharField(blank=True, max_length=100)),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("depth", models.PositiveSmallIntegerField(default=0)),
                ("scraped_at", models.DateTimeField(auto_now_add=True)),
                ("research_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scraped_pages", to="research.researchjob")),
            ],
            options={"ordering": ["scraped_at"]},
        ),
        migrations.AddConstraint(
            model_name="scrapedpage",
            constraint=models.UniqueConstraint(fields=("research_job", "url_hash"), name="unique_scraped_url_per_job"),
        ),
    ]
