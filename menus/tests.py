from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from menus.models import Menu, MenuItem
from recipes.models import Recipe

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
