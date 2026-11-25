from rest_framework import serializers


class SuggestionSerializer(serializers.Serializer):
    recipe_id = serializers.IntegerField()
    title = serializers.CharField()
    amount_needed = serializers.FloatField()


class LeftoverSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    leftover = serializers.FloatField()
    unit = serializers.CharField()
    shelf_life_days = serializers.IntegerField(allow_null=True)
    suggestions = SuggestionSerializer(many=True)


class LeftoversResponseSerializer(serializers.Serializer):
    """Лише для Swagger."""

    leftovers = LeftoverSerializer(many=True)
