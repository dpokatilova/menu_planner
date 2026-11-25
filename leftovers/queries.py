from decimal import Decimal

from django.db.models import Sum

from leftovers.services import to_number
from recipes.models import Product, Recipe, RecipeIngredient

MAX_SUGGESTIONS = 3


def get_products_info(product_ids):
    products = Product.objects.filter(id__in=product_ids)
    return {
        product.id: {
            "is_packaged": product.is_packaged,
            "package_size": product.package_size,
            "unit": product.unit,
            "shelf_life_days": product.shelf_life_days,
        }
        for product in products
    }


def find_suggestions(product_id, unit, leftover, exclude_recipe_ids, limit=MAX_SUGGESTIONS):
    # Сумуємо за рецептом: той самий продукт може бути в одному рецепті двічі.
    rows = (
        RecipeIngredient.objects.filter(
            product_id=product_id, unit=unit, recipe__status=Recipe.Status.APPROVED
        )
        .exclude(recipe_id__in=exclude_recipe_ids)
        .values("recipe_id", "recipe__title")
        .annotate(total=Sum("amount"))
        .filter(total__gt=0, total__lte=Decimal(str(leftover)))
        .order_by("-total", "recipe_id")[:limit]
    )
    return [
        {
            "recipe_id": row["recipe_id"],
            "title": row["recipe__title"],
            "amount_needed": to_number(row["total"]),
        }
        for row in rows
    ]
