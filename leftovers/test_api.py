import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from menus.models import Menu, MenuItem
from recipes.models import Product, Recipe, RecipeIngredient

User = get_user_model()
WEEK_START = datetime.date(2026, 11, 23)


class LeftoversApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw-12345-xyz")
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}")

        self.cream = Product.objects.create(
            name="Сметана", is_packaged=True, package_size=250, unit="g", shelf_life_days=5
        )
        self.menu = Menu.objects.create(user=self.user, week_start=WEEK_START)
        self.tuesday_dish = self.make_recipe("Борщ", 100)
        self.thursday_dish = self.make_recipe("Салат", 50)
        self.add_to_menu(self.tuesday_dish, day=1)
        self.add_to_menu(self.thursday_dish, day=3)

    def make_recipe(self, title, amount, product=None, unit="g"):
        recipe = Recipe.objects.create(title=title, status=Recipe.Status.APPROVED)
        RecipeIngredient.objects.create(
            recipe=recipe, product=product or self.cream, amount=amount, unit=unit
        )
        return recipe

    def add_to_menu(self, recipe, day, menu=None, meal_type="lunch"):
        MenuItem.objects.create(
            menu=menu or self.menu,
            recipe=recipe,
            date=WEEK_START + datetime.timedelta(days=day),
            meal_type=meal_type,
        )

    def get(self, menu_id=None):
        return self.client.get(f"/api/menus/{menu_id or self.menu.id}/leftovers/")

    def test_example_from_spec(self):
        soup = self.make_recipe("Соус", 80)

        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "leftovers": [
                    {
                        "product_id": self.cream.id,
                        "product_name": "Сметана",
                        "leftover": 100,
                        "unit": "g",
                        "shelf_life_days": 5,
                        "suggestions": [
                            {"recipe_id": soup.id, "title": "Соус", "amount_needed": 80}
                        ],
                    }
                ]
            },
        )

    def test_recipes_from_the_menu_are_not_suggested(self):
        response = self.get()

        self.assertEqual(response.json()["leftovers"][0]["suggestions"], [])

    def test_leftover_without_fitting_recipes_has_empty_suggestions(self):
        self.make_recipe("Торт", 150)

        entry = self.get().json()["leftovers"][0]

        self.assertEqual(entry["suggestions"], [])
        self.assertEqual(entry["leftover"], 100)

    def test_missing_shelf_life_is_null(self):
        self.cream.shelf_life_days = None
        self.cream.save()

        entry = self.get().json()["leftovers"][0]

        self.assertIsNone(entry["shelf_life_days"])

    def test_product_without_leftover_is_not_listed(self):
        self.thursday_dish.ingredients.update(amount=150)

        self.assertEqual(self.get().json(), {"leftovers": []})

    def test_leftover_below_20_percent_is_not_listed(self):
        self.thursday_dish.ingredients.update(amount=101)

        self.assertEqual(self.get().json(), {"leftovers": []})

    def test_not_packaged_product_is_skipped(self):
        self.cream.is_packaged = False
        self.cream.save()

        self.assertEqual(self.get().json(), {"leftovers": []})

    def test_product_with_other_unit_is_skipped(self):
        self.cream.unit = "ml"
        self.cream.save()

        self.assertEqual(self.get().json(), {"leftovers": []})

    def test_empty_menu_gives_empty_list(self):
        empty = Menu.objects.create(user=self.user, week_start=WEEK_START + datetime.timedelta(days=7))

        self.assertEqual(self.get(empty.id).json(), {"leftovers": []})

    def test_foreign_menu_returns_404(self):
        other = User.objects.create_user("other", password="pw-12345-xyz")
        foreign = Menu.objects.create(user=other, week_start=WEEK_START + datetime.timedelta(days=7))

        self.assertEqual(self.get(foreign.id).status_code, 404)

    def test_unknown_menu_returns_404(self):
        self.assertEqual(self.get(99999).status_code, 404)

    def test_without_token_returns_401(self):
        response = APIClient().get(f"/api/menus/{self.menu.id}/leftovers/")

        self.assertEqual(response.status_code, 401)

    def test_suggestions_are_sorted_and_limited_to_three(self):
        for amount in (10, 20, 30, 40, 50):
            self.make_recipe(f"R{amount}", amount)

        suggestions = self.get().json()["leftovers"][0]["suggestions"]

        self.assertEqual([s["amount_needed"] for s in suggestions], [50, 40, 30])

    def test_pending_recipes_are_not_suggested(self):
        draft = self.make_recipe("Чернетка", 50)
        draft.status = Recipe.Status.PENDING
        draft.save()

        self.assertEqual(self.get().json()["leftovers"][0]["suggestions"], [])
