from django.test import TestCase

from leftovers.queries import find_suggestions, get_products_info
from recipes.models import Product, Recipe, RecipeIngredient


class FindSuggestionsTests(TestCase):
    def setUp(self):
        self.cream = Product.objects.create(
            name="Сметана", is_packaged=True, package_size=250, unit="g", shelf_life_days=5
        )
        self.flour = Product.objects.create(name="Борошно", unit="g")

    def make_recipe(self, title, amount, product=None, unit="g", status=Recipe.Status.APPROVED):
        recipe = Recipe.objects.create(title=title, status=status)
        RecipeIngredient.objects.create(
            recipe=recipe, product=product or self.cream, amount=amount, unit=unit
        )
        return recipe

    def suggest(self, leftover=100, exclude=()):
        return find_suggestions(self.cream.id, "g", leftover, exclude)

    def test_suggests_recipe_that_fits_leftover(self):
        recipe = self.make_recipe("Соус", 80)

        result = self.suggest()

        self.assertEqual(result, [{"recipe_id": recipe.id, "title": "Соус", "amount_needed": 80}])

    def test_recipe_bigger_than_leftover_is_dropped(self):
        self.make_recipe("Торт", 120)

        self.assertEqual(self.suggest(), [])

    def test_recipe_equal_to_leftover_is_included(self):
        self.make_recipe("Борщ", 100)

        self.assertEqual(len(self.suggest()), 1)

    def test_sorted_by_share_of_leftover_descending(self):
        self.make_recipe("Мало", 30)
        self.make_recipe("Багато", 90)
        self.make_recipe("Середньо", 60)

        titles = [s["title"] for s in self.suggest()]

        self.assertEqual(titles, ["Багато", "Середньо", "Мало"])

    def test_equal_shares_are_ordered_by_recipe_id(self):
        first = self.make_recipe("Перший", 50)
        second = self.make_recipe("Другий", 50)

        ids = [s["recipe_id"] for s in self.suggest()]

        self.assertEqual(ids, [first.id, second.id])

    def test_returns_at_most_three(self):
        for i in range(5):
            self.make_recipe(f"R{i}", 10 + i)

        self.assertEqual(len(self.suggest()), 3)

    def test_best_three_are_kept(self):
        for amount in (10, 20, 30, 40, 50):
            self.make_recipe(f"R{amount}", amount)

        amounts = [s["amount_needed"] for s in self.suggest()]

        self.assertEqual(amounts, [50, 40, 30])

    def test_recipes_already_in_menu_are_excluded(self):
        in_menu = self.make_recipe("В меню", 90)
        other = self.make_recipe("Інший", 60)

        result = self.suggest(exclude={in_menu.id})

        self.assertEqual([s["recipe_id"] for s in result], [other.id])

    def test_only_approved_recipes_are_suggested(self):
        self.make_recipe("Чернетка", 50, status=Recipe.Status.PENDING)
        self.make_recipe("Відхилений", 50, status=Recipe.Status.REJECTED)

        self.assertEqual(self.suggest(), [])

    def test_ingredient_with_other_unit_is_ignored(self):
        self.make_recipe("У мілілітрах", 50, unit="ml")

        self.assertEqual(self.suggest(), [])

    def test_ingredients_of_other_products_are_ignored(self):
        self.make_recipe("Млинці", 50, product=self.flour)

        self.assertEqual(self.suggest(), [])

    def test_same_product_twice_in_recipe_is_summed(self):
        recipe = self.make_recipe("Подвійний", 60)
        RecipeIngredient.objects.create(recipe=recipe, product=self.cream, amount=60, unit="g")

        self.assertEqual(self.suggest(leftover=100), [])

    def test_same_product_twice_fits_when_sum_is_small(self):
        recipe = self.make_recipe("Подвійний", 40)
        RecipeIngredient.objects.create(recipe=recipe, product=self.cream, amount=40, unit="g")

        result = self.suggest(leftover=100)

        self.assertEqual(result[0]["amount_needed"], 80)

    def test_fractional_leftover_boundary(self):
        self.make_recipe("Рівно", "62.50")
        self.make_recipe("Трохи більше", "62.51")

        titles = [s["title"] for s in self.suggest(leftover=62.5)]

        self.assertEqual(titles, ["Рівно"])

    def test_no_recipes_gives_empty_list(self):
        self.assertEqual(self.suggest(), [])


class GetProductsInfoTests(TestCase):
    def test_returns_packaging_fields(self):
        product = Product.objects.create(
            name="Молоко", is_packaged=True, package_size=1000, unit="ml", shelf_life_days=7
        )

        info = get_products_info([product.id])

        self.assertEqual(
            info[product.id],
            {"is_packaged": True, "package_size": 1000, "unit": "ml", "shelf_life_days": 7},
        )

    def test_unknown_ids_are_missing(self):
        self.assertEqual(get_products_info([99999]), {})
