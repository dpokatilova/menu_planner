from rest_framework import serializers

from recipes.models import Category, DietTag, Product, Recipe, RecipeIngredient


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "kind")


class DietTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietTag
        fields = ("id", "name", "slug")


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "unit", "is_packaged", "package_size")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product.name", read_only=True)
    product_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ("product_id", "product", "amount", "unit")


class RecipeListSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    diet_tags = DietTagSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "title",
            "image_url",
            "cooking_time_min",
            "calories",
            "servings",
            "categories",
            "diet_tags",
        )


class RecipeDetailSerializer(RecipeListSerializer):
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)

    class Meta(RecipeListSerializer.Meta):
        fields = RecipeListSerializer.Meta.fields + (
            "description",
            "instructions",
            "ingredients",
        )
