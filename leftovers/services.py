from decimal import Decimal

MIN_LEFTOVER_RATIO = Decimal("0.2")


def _to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _to_number(value: Decimal):
    """100, а не Decimal("100"): щоб у JSON було число, а не рядок."""
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def calculate_leftovers(shopping_items, products_info):
    """Для кожного упакованого продукту рахує залишок після закупівлі за списком покупок."""
    result = []
    for item in shopping_items:
        info = products_info.get(item["product_id"])
        if not info or not info.get("is_packaged") or not info.get("package_size"):
            continue
        if info.get("unit") != item["unit"]:
            continue

        needed = _to_decimal(item["amount"])
        package_size = _to_decimal(info["package_size"])
        if needed <= 0 or package_size <= 0:
            continue

        # // для Decimal усікає до нуля (не вниз, як для int), тому -(-a // b) тут не працює.
        packages = needed // package_size
        if packages * package_size < needed:
            packages += 1
        leftover = packages * package_size - needed

        if leftover >= package_size * MIN_LEFTOVER_RATIO:
            result.append(
                {
                    "product_id": item["product_id"],
                    "product_name": item.get("product_name", ""),
                    "leftover": _to_number(leftover),
                    "unit": item["unit"],
                    "shelf_life_days": info.get("shelf_life_days"),
                }
            )
    return result
