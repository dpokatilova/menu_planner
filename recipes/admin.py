from django.contrib import admin

from recipes.models import Category, DietTag, Product, Recipe, RecipeIngredient


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "source", "author", "created_at")
    list_filter = ("status", "source", "categories", "diet_tags")
    search_fields = ("title",)
    inlines = [RecipeIngredientInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "is_packaged", "package_size", "unit", "shelf_life_days")
    list_filter = ("is_packaged",)
    search_fields = ("name",)


admin.site.register(Category)
admin.site.register(DietTag)
