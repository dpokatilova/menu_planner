from decimal import Decimal

from django.test import SimpleTestCase

from leftovers.services import calculate_leftovers


def item(amount, product_id=7, unit="g", name="Сметана"):
    return {"product_id": product_id, "product_name": name, "amount": amount, "unit": unit}


def info(size=250, packaged=True, unit="g", shelf=5):
    return {"is_packaged": packaged, "package_size": size, "unit": unit, "shelf_life_days": shelf}


class CalculateLeftoversTests(SimpleTestCase):
    def test_150_of_250_leaves_100(self):
        result = calculate_leftovers([item(150)], {7: info()})

        self.assertEqual(
            result,
            [
                {
                    "product_id": 7,
                    "product_name": "Сметана",
                    "leftover": 100,
                    "unit": "g",
                    "shelf_life_days": 5,
                }
            ],
        )

    def test_zero_leftover_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(250)], {7: info()}), [])

    def test_zero_leftover_with_several_packages_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(500)], {7: info()}), [])

    def test_several_packages(self):
        result = calculate_leftovers([item(300)], {7: info()})

        self.assertEqual(result[0]["leftover"], 200)

    def test_exactly_20_percent_is_included(self):
        result = calculate_leftovers([item(200)], {7: info()})

        self.assertEqual(result[0]["leftover"], 50)

    def test_just_below_20_percent_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(201)], {7: info()}), [])

    def test_20_percent_boundary_with_decimals(self):
        result = calculate_leftovers([item(Decimal("0.8"))], {7: info(size=Decimal("1"))})

        self.assertEqual(len(result), 1)

    def test_not_packaged_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(150)], {7: info(packaged=False)}), [])

    def test_missing_package_size_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(150)], {7: info(size=None)}), [])

    def test_unknown_product_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(150, product_id=99)], {7: info()}), [])

    def test_unit_mismatch_is_skipped(self):
        self.assertEqual(calculate_leftovers([item(150, unit="ml")], {7: info(unit="g")}), [])

    def test_missing_shelf_life_stays_none(self):
        result = calculate_leftovers([item(150)], {7: info(shelf=None)})

        self.assertIsNone(result[0]["shelf_life_days"])

    def test_empty_shopping_list(self):
        self.assertEqual(calculate_leftovers([], {7: info()}), [])

    def test_keeps_order_and_skips_products_without_leftover(self):
        items = [item(150, 1, name="A"), item(250, 2, name="B"), item(100, 3, name="C")]
        products = {1: info(), 2: info(), 3: info(size=500)}

        result = calculate_leftovers(items, products)

        self.assertEqual([r["product_id"] for r in result], [1, 3])

    def test_fractional_leftover_is_float(self):
        result = calculate_leftovers([item(Decimal("187.5"))], {7: info()})

        self.assertEqual(result[0]["leftover"], 62.5)

    def test_accepts_float_and_string_numbers(self):
        result = calculate_leftovers([item(150.0)], {7: info(size="250.00")})

        self.assertEqual(result[0]["leftover"], 100)
