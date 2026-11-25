from datetime import date
from decimal import Decimal


from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from menus.models import Menu, MenuItem
from menus.services import build_shopping_list
from recipes.models import Recipe
from recipes.models import Product, RecipeIngredient, Unit

User = get_user_model()

MONDAY = date(2026, 11, 23)
TUESDAY = date(2026, 11, 24)
NEXT_MONDAY = date(2026, 11, 30)
OUT_OF_WEEK = date(2026, 12, 15)


class MenuTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="dasha", password="VeryStrongPass123"
        )
        cls.other = User.objects.create_user(
            username="someone", password="VeryStrongPass123"
        )
        cls.approved = Recipe.objects.create(
            title="Сирники", status=Recipe.Status.APPROVED
        )
        cls.another = Recipe.objects.create(
            title="Омлет", status=Recipe.Status.APPROVED
        )
        cls.pending = Recipe.objects.create(
            title="Чернетка", status=Recipe.Status.PENDING
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def create_menu(self, user=None, week_start=MONDAY, menu_status=Menu.Status.DRAFT):
        return Menu.objects.create(
            user=user or self.user, week_start=week_start, status=menu_status
        )

    def add_item(self, menu, recipe=None, day=MONDAY, meal_type="breakfast"):
        return MenuItem.objects.create(
            menu=menu, recipe=recipe or self.approved, date=day, meal_type=meal_type
        )


class MenuCreateTests(MenuTestCase):
    def test_create_draft_menu(self):
        response = self.client.post(reverse("menu-list"), {"week_start": MONDAY})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Menu.Status.DRAFT)
        self.assertEqual(response.data["items"], [])

    def test_week_must_start_on_monday(self):
        response = self.client.post(reverse("menu-list"), {"week_start": TUESDAY})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("week_start", response.data)

    def test_one_menu_per_week(self):
        self.create_menu()
        response = self.client.post(reverse("menu-list"), {"week_start": MONDAY})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_week_allowed_for_another_user(self):
        self.create_menu(user=self.other)
        response = self.client.post(reverse("menu-list"), {"week_start": MONDAY})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse("menu-list"), {"week_start": MONDAY})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MenuAccessTests(MenuTestCase):
    def test_list_shows_only_own_menus(self):
        self.create_menu()
        self.create_menu(user=self.other, week_start=NEXT_MONDAY)
        response = self.client.get(reverse("menu-list"))
        self.assertEqual(response.data["count"], 1)

    def test_foreign_menu_returns_404(self):
        foreign = self.create_menu(user=self.other)
        response = self.client.get(reverse("menu-detail", args=[foreign.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_foreign_menu(self):
        foreign = self.create_menu(user=self.other)
        response = self.client.delete(reverse("menu-detail", args=[foreign.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Menu.objects.filter(id=foreign.id).exists())

    def test_cannot_add_item_to_foreign_menu(self):
        foreign = self.create_menu(user=self.other)
        response = self.client.post(
            reverse("menu-item-create", args=[foreign.id]),
            {"recipe": self.approved.id, "date": MONDAY, "meal_type": "breakfast"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MenuItemTests(MenuTestCase):
    def setUp(self):
        super().setUp()
        self.menu = self.create_menu()
        self.url = reverse("menu-item-create", args=[self.menu.id])

    def test_add_approved_recipe(self):
        response = self.client.post(
            self.url,
            {"recipe": self.approved.id, "date": MONDAY, "meal_type": "breakfast"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recipe_title"], "Сирники")

    def test_pending_recipe_rejected(self):
        response = self.client.post(
            self.url,
            {"recipe": self.pending.id, "date": MONDAY, "meal_type": "breakfast"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_outside_week_rejected(self):
        response = self.client.post(
            self.url,
            {"recipe": self.approved.id, "date": OUT_OF_WEEK, "meal_type": "breakfast"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data)

    def test_slot_taken_rejected(self):
        self.add_item(self.menu)
        response = self.client.post(
            self.url,
            {"recipe": self.another.id, "date": MONDAY, "meal_type": "breakfast"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_day_other_meal_allowed(self):
        self.add_item(self.menu, meal_type="breakfast")
        response = self.client.post(
            self.url,
            {"recipe": self.another.id, "date": MONDAY, "meal_type": "dinner"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_item(self):
        item = self.add_item(self.menu)
        response = self.client.delete(
            reverse("menu-item-delete", args=[self.menu.id, item.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MenuItem.objects.filter(id=item.id).exists())

    def test_menu_detail_contains_items(self):
        self.add_item(self.menu)
        response = self.client.get(reverse("menu-detail", args=[self.menu.id]))
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["recipe_title"], "Сирники")


class MenuSaveTests(MenuTestCase):
    def test_cannot_save_empty_menu(self):
        menu = self.create_menu()
        response = self.client.post(reverse("menu-save", args=[menu.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        menu.refresh_from_db()
        self.assertEqual(menu.status, Menu.Status.DRAFT)

    def test_save_menu_with_items(self):
        menu = self.create_menu()
        self.add_item(menu)
        response = self.client.post(reverse("menu-save", args=[menu.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        menu.refresh_from_db()
        self.assertEqual(menu.status, Menu.Status.SAVED)

    def test_saved_menu_can_still_be_edited(self):
        menu = self.create_menu(menu_status=Menu.Status.SAVED)
        response = self.client.post(
            reverse("menu-item-create", args=[menu.id]),
            {"recipe": self.approved.id, "date": MONDAY, "meal_type": "lunch"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class MenuHistoryTests(MenuTestCase):
    def test_history_shows_only_saved_menus(self):
        self.create_menu(week_start=MONDAY, menu_status=Menu.Status.SAVED)
        self.create_menu(week_start=NEXT_MONDAY, menu_status=Menu.Status.DRAFT)

        response = self.client.get(reverse("menu-list"), {"status": "saved"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], Menu.Status.SAVED)

    def test_history_newest_first(self):
        self.create_menu(week_start=MONDAY, menu_status=Menu.Status.SAVED)
        self.create_menu(week_start=NEXT_MONDAY, menu_status=Menu.Status.SAVED)

        response = self.client.get(reverse("menu-list"), {"status": "saved"})
        weeks = [item["week_start"] for item in response.data["results"]]
        self.assertEqual(weeks, [str(NEXT_MONDAY), str(MONDAY)])


class ShoppingListTests(MenuTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.milk = Product.objects.create(
            name="Молоко",
            unit=Unit.MILLILITER,
            is_packaged=True,
            package_size=Decimal("1000"),
        )
        cls.eggs = Product.objects.create(name="Яйця", unit=Unit.PIECE)
        cls.sugar = Product.objects.create(
            name="Цукор",
            unit=Unit.GRAM,
            is_packaged=True,
            package_size=Decimal("1000"),
        )

        RecipeIngredient.objects.create(
            recipe=cls.approved, product=cls.milk, amount=200, unit=Unit.MILLILITER
        )
        RecipeIngredient.objects.create(
            recipe=cls.approved, product=cls.eggs, amount=2, unit=Unit.PIECE
        )
        RecipeIngredient.objects.create(
            recipe=cls.another, product=cls.milk, amount=300, unit=Unit.MILLILITER
        )

    def setUp(self):
        super().setUp()
        self.menu = self.create_menu()
        self.url = reverse("menu-shopping-list", args=[self.menu.id])

    def rows(self, response):
        return {row["product_name"]: row for row in response.data["items"]}

    def test_empty_menu_gives_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])

    def test_amounts_are_summed_across_recipes(self):
        self.add_item(self.menu, recipe=self.approved, meal_type="breakfast")
        self.add_item(self.menu, recipe=self.another, meal_type="dinner")

        rows = self.rows(self.client.get(self.url))
        self.assertEqual(rows["Молоко"]["amount"], 500)
        self.assertEqual(rows["Яйця"]["amount"], 2)

    def test_same_recipe_twice_counts_twice(self):
        self.add_item(self.menu, recipe=self.approved, meal_type="breakfast")
        self.add_item(
            self.menu, recipe=self.approved, day=TUESDAY, meal_type="breakfast"
        )

        rows = self.rows(self.client.get(self.url))
        self.assertEqual(rows["Молоко"]["amount"], 400)
        self.assertEqual(rows["Яйця"]["amount"], 4)

    def test_packages_rounded_up(self):
        self.add_item(self.menu, recipe=self.approved)
        rows = self.rows(self.client.get(self.url))
        self.assertEqual(rows["Молоко"]["packages_needed"], 1)

    def test_several_packages_needed(self):
        for day, meal in (
            (MONDAY, "breakfast"),
            (MONDAY, "lunch"),
            (MONDAY, "dinner"),
            (MONDAY, "snack"),
            (TUESDAY, "breakfast"),
        ):
            self.add_item(self.menu, recipe=self.another, day=day, meal_type=meal)

        rows = self.rows(self.client.get(self.url))
        self.assertEqual(rows["Молоко"]["amount"], 1500)
        self.assertEqual(rows["Молоко"]["packages_needed"], 2)

    def test_unpackaged_product_has_no_packages(self):
        self.add_item(self.menu, recipe=self.approved)
        rows = self.rows(self.client.get(self.url))
        self.assertIsNone(rows["Яйця"]["packages_needed"])

    def test_different_units_are_separate_rows(self):
        odd = Recipe.objects.create(title="Дивний", status=Recipe.Status.APPROVED)
        RecipeIngredient.objects.create(
            recipe=odd, product=self.milk, amount=100, unit=Unit.GRAM
        )
        self.add_item(self.menu, recipe=self.approved, meal_type="breakfast")
        self.add_item(self.menu, recipe=odd, meal_type="dinner")

        items = self.client.get(self.url).data["items"]
        milk_rows = [row for row in items if row["product_name"] == "Молоко"]
        self.assertEqual(len(milk_rows), 2)

        by_unit = {row["unit"]: row for row in milk_rows}
        self.assertEqual(by_unit["ml"]["amount"], 200)
        self.assertEqual(by_unit["g"]["amount"], 100)
        self.assertIsNone(by_unit["g"]["packages_needed"])

    def test_sorted_by_product_name(self):
        self.add_item(self.menu, recipe=self.approved)
        names = [row["product_name"] for row in self.client.get(self.url).data["items"]]
        self.assertEqual(names, sorted(names))

    def test_foreign_menu_returns_404(self):
        foreign = self.create_menu(user=self.other, week_start=NEXT_MONDAY)
        response = self.client.get(
            reverse("menu-shopping-list", args=[foreign.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BuildShoppingListFunctionTests(MenuTestCase):
    def test_empty_input(self):
        self.assertEqual(build_shopping_list([]), [])
