from __future__ import annotations

from urllib.parse import urlsplit

from django.conf import settings
from rest_framework import serializers

from research.models import ResearchJob


class ResearchRequestSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=2048, trim_whitespace=True)
    prompt = serializers.CharField(trim_whitespace=True)

    def validate_url(self, value: str) -> str:
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError as exc:
            raise serializers.ValidationError("The provided website URL is invalid.") from exc
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise serializers.ValidationError("Only valid HTTP and HTTPS URLs are supported.")
        return value

    def validate_prompt(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("A research prompt is required.")
        if len(value) > settings.MAX_PROMPT_LENGTH:
            raise serializers.ValidationError(f"The prompt must be at most {settings.MAX_PROMPT_LENGTH} characters.")
        return value


class ResearchJobSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="uuid", read_only=True)
    prompt = serializers.CharField(source="user_prompt", read_only=True)
    answer = serializers.CharField(source="final_answer", read_only=True)

    class Meta:
        model = ResearchJob
        fields = (
            "job_id",
            "status",
            "current_stage",
            "website_url",
            "prompt",
            "answer",
            "sources",
            "pages_scraped",
            "retrieval_iterations",
            "crawl_iterations",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
        )
