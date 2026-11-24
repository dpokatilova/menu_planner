from django.urls import path

from recipes.views import CategoryListView, DietTagListView, ProductListView, RecipeDetailView, RecipeListView

urlpatterns = [
    path("recipes/", RecipeListView.as_view(), name="recipe-list"),
    path("recipes/<int:pk>/", RecipeDetailView.as_view(), name="recipe-detail"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("diet-tags/", DietTagListView.as_view(), name="diet-tag-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
]
