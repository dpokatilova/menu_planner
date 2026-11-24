from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai import services
from ai.serializers import RecommendationRequestSerializer, RecommendationResponseSerializer


class RecommendationsView(APIView):

    permission_classes = [IsAuthenticated]
    throttle_scope = "ai"

    @extend_schema(
        request=RecommendationRequestSerializer,
        responses=RecommendationResponseSerializer,
    )
    def post(self, request):
        serializer = RecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.recommend(
            query=data["query"],
            diet_tag_slugs=[tag.slug for tag in data.get("diet_tags", [])],
            max_calories=data.get("max_calories"),
            count=data["count"],
        )
        return Response(result)
