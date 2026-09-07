from django.contrib import admin

from .models import ResearchJob, ScrapedPage


@admin.register(ResearchJob)
class ResearchJobAdmin(admin.ModelAdmin):
    list_display = ("uuid", "website_url", "status", "current_stage", "pages_scraped", "created_at", "completed_at")
    list_filter = ("status", "current_stage", "created_at")
    search_fields = ("=uuid", "website_url", "user_prompt", "error_message")
    readonly_fields = ("uuid", "created_at", "started_at", "completed_at")


@admin.register(ScrapedPage)
class ScrapedPageAdmin(admin.ModelAdmin):
    list_display = ("url", "research_job", "scrape_status", "status_code", "word_count", "depth", "scraped_at")
    list_filter = ("scrape_status", "status_code", "depth", "scraped_at")
    search_fields = ("url", "title", "content_hash", "=research_job__uuid")
    readonly_fields = ("url_hash", "content_hash", "scraped_at")
