from rest_framework import generics, permissions

from recipes.filters import RecipeFilter
from recipes.models import Category, DietTag, Product, Recipe
from recipes.pagination import RecipePagination
from recipes.serializers import (
    CategorySerializer,
    DietTagSerializer,
    ProductSerializer,
    RecipeDetailSerializer,
    RecipeListSerializer,
)


class ApprovedRecipeQuerysetMixin:
    def get_queryset(self):
        return Recipe.objects.filter(status=Recipe.Status.APPROVED).prefetch_related("categories", "diet_tags")


class RecipeListView(ApprovedRecipeQuerysetMixin, generics.ListAPIView):
    serializer_class = RecipeListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = RecipePagination
    filterset_class = RecipeFilter
    ordering_fields = ("cooking_time_min", "calories", "created_at")
    ordering = ("-created_at",)


class RecipeDetailView(ApprovedRecipeQuerysetMixin, generics.RetrieveAPIView):
    serializer_class = RecipeDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return super().get_queryset().prefetch_related("ingredients__product")


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class DietTagListView(generics.ListAPIView):
    queryset = DietTag.objects.all()
    serializer_class = DietTagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = RecipePagination
