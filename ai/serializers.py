from rest_framework import serializers

from recipes.models import DietTag


class RecommendationRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=300)
    diet_tags = serializers.SlugRelatedField(
        many=True,
        slug_field="slug",
        queryset=DietTag.objects.all(),
        required=False,
    )
    max_calories = serializers.IntegerField(min_value=1, required=False)
    count = serializers.IntegerField(min_value=3, max_value=5, default=3)


class RecommendedRecipeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    reason = serializers.CharField(allow_null=True)


class RecommendationResponseSerializer(serializers.Serializer):

    ai_used = serializers.BooleanField()
    disclaimer = serializers.CharField()
    recipes = RecommendedRecipeSerializer(many=True)
