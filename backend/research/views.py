from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from research.exceptions import ResearchError
from research.models import ResearchJob
from research.serializers import ResearchJobSerializer, ResearchRequestSerializer
from research.services.research_runner import ResearchRunner

logger = logging.getLogger("research.api")


class ResearchCreateView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        serializer = ResearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = ResearchJob.objects.create(
            website_url=serializer.validated_data["url"],
            user_prompt=serializer.validated_data["prompt"],
        )
        try:
            ResearchRunner().run(job)
        except ResearchError as exc:
            return Response({"error": {"code": exc.code, "message": exc.public_message}}, status=exc.status_code)
        except Exception:
            logger.error("unhandled_research_error job_id=%s", job.uuid)
            return Response(
                {"error": {"code": "research_failed", "message": "The website research could not be completed."}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(ResearchJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ResearchDetailView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, job_uuid):
        job = get_object_or_404(ResearchJob, uuid=job_uuid)
        return Response(ResearchJobSerializer(job).data)
