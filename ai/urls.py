from django.urls import path

from ai.views import RecommendationsView

urlpatterns = [
    path("recommendations/", RecommendationsView.as_view(), name="ai-recommendations"),
]
