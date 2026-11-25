from collections import defaultdict
from decimal import Decimal
from math import ceil


def build_shopping_list(menu_items):
    totals = defaultdict(Decimal)
    products = {}

    for menu_item in menu_items:
        for ingredient in menu_item.recipe.ingredients.all():
            key = (ingredient.product_id, ingredient.unit)
            totals[key] += ingredient.amount
            products[ingredient.product_id] = ingredient.product

    rows = []
    for (product_id, unit), amount in totals.items():
        product = products[product_id]

        packages_needed = None
        if product.is_packaged and product.package_size and product.unit == unit:
            packages_needed = ceil(amount / product.package_size)

        rows.append(
            {
                "product_id": product_id,
                "product_name": product.name,
                "amount": amount,
                "unit": unit,
                "packages_needed": packages_needed,
            }
        )

    rows.sort(key=lambda row: row["product_name"])
    return rows
