from django.urls import path

from research.views import ResearchCreateView, ResearchDetailView

urlpatterns = [
    path("research/", ResearchCreateView.as_view(), name="research-create"),
    path("research/<uuid:job_uuid>/", ResearchDetailView.as_view(), name="research-detail"),
]

