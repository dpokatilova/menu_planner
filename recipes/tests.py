from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from recipes.models import Category, DietTag, Product, Recipe, RecipeIngredient, Unit


class CatalogTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.breakfast = Category.objects.create(
            name="Сніданки", slug="breakfast", kind=Category.Kind.MEAL_TYPE
        )
        cls.italian = Category.objects.create(
            name="Італійська кухня", slug="italian", kind=Category.Kind.CUISINE
        )
        cls.gluten_free = DietTag.objects.create(
            name="Без глютену", slug="gluten_free"
        )
        cls.vegetarian = DietTag.objects.create(
            name="Вегетаріанське", slug="vegetarian"
        )
        cls.cheese = Product.objects.create(name="Сир", unit=Unit.GRAM)
        cls.flour = Product.objects.create(name="Борошно", unit=Unit.GRAM)
        cls.syrnyky = Recipe.objects.create(
            title="Сирники",
            status=Recipe.Status.APPROVED,
            cooking_time_min=20,
            calories=320,
        )
        cls.syrnyky.categories.add(cls.breakfast)
        cls.syrnyky.diet_tags.add(cls.gluten_free, cls.vegetarian)
        RecipeIngredient.objects.create(
            recipe=cls.syrnyky, product=cls.cheese, amount=400, unit=Unit.GRAM
        )
        cls.pasta = Recipe.objects.create(
            title="Паста болоньєзе",
            status=Recipe.Status.APPROVED,
            cooking_time_min=60,
            calories=800,
        )
        cls.pasta.categories.add(cls.italian)
        cls.pasta.diet_tags.add(cls.vegetarian)
        RecipeIngredient.objects.create(
            recipe=cls.pasta, product=cls.flour, amount=200, unit=Unit.GRAM
        )
        cls.hidden = Recipe.objects.create(
            title="Чернетка", status=Recipe.Status.PENDING
        )
        cls.rejected = Recipe.objects.create(
            title="Відхилений", status=Recipe.Status.REJECTED
        )

    def titles(self, response):
        return [item["title"] for item in response.data["results"]]


class RecipeListTests(CatalogTestCase):
    def test_list_available_to_guest(self):
        response = self.client.get(reverse("recipe-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_approved_recipes_listed(self):
        response = self.client.get(reverse("recipe-list"))
        self.assertEqual(response.data["count"], 2)
        self.assertNotIn("Чернетка", self.titles(response))
        self.assertNotIn("Відхилений", self.titles(response))

    def test_search_is_case_insensitive_for_cyrillic(self):
        response = self.client.get(reverse("recipe-list"), {"search": "сирник"})
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_search_uppercase_query(self):
        response = self.client.get(reverse("recipe-list"), {"search": "СИРНИКИ"})
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_filter_by_category(self):
        response = self.client.get(reverse("recipe-list"), {"category": "italian"})
        self.assertEqual(self.titles(response), ["Паста болоньєзе"])

    def test_filter_by_single_diet_tag(self):
        response = self.client.get(reverse("recipe-list"), {"diet_tag": "vegetarian"})
        self.assertEqual(response.data["count"], 2)

    def test_filter_by_several_diet_tags_requires_all(self):
        response = self.client.get(
            reverse("recipe-list"), {"diet_tag": "vegetarian,gluten_free"}
        )
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_filter_by_product(self):
        response = self.client.get(
            reverse("recipe-list"), {"product": self.cheese.id}
        )
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_filter_by_max_time(self):
        response = self.client.get(reverse("recipe-list"), {"max_time": 30})
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_filter_by_max_calories(self):
        response = self.client.get(reverse("recipe-list"), {"max_calories": 500})
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_filters_combine(self):
        response = self.client.get(
            reverse("recipe-list"),
            {"diet_tag": "vegetarian", "max_time": 30, "category": "breakfast"},
        )
        self.assertEqual(self.titles(response), ["Сирники"])

    def test_ordering_ascending(self):
        response = self.client.get(reverse("recipe-list"), {"ordering": "calories"})
        self.assertEqual(self.titles(response), ["Сирники", "Паста болоньєзе"])

    def test_ordering_descending(self):
        response = self.client.get(reverse("recipe-list"), {"ordering": "-calories"})
        self.assertEqual(self.titles(response), ["Паста болоньєзе", "Сирники"])

    def test_no_duplicates_when_filtering_by_tag(self):
        response = self.client.get(reverse("recipe-list"), {"max_time": 30})
        self.assertEqual(len(response.data["results"]), response.data["count"])


class PaginationTests(CatalogTestCase):
    def test_pagination_fields_present(self):
        response = self.client.get(reverse("recipe-list"))
        for field in ("count", "next", "previous", "results"):
            self.assertIn(field, response.data)

    def test_custom_page_size(self):
        response = self.client.get(reverse("recipe-list"), {"page_size": 1})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])

    def test_second_page(self):
        response = self.client.get(
            reverse("recipe-list"), {"page_size": 1, "page": 2}
        )
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["previous"])

    def test_page_size_capped_at_max(self):
        response = self.client.get(reverse("recipe-list"), {"page_size": 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_page_out_of_range(self):
        response = self.client.get(reverse("recipe-list"), {"page": 99})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RecipeDetailTests(CatalogTestCase):
    def test_detail_returns_ingredients(self):
        response = self.client.get(
            reverse("recipe-detail", args=[self.syrnyky.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Сирники")
        self.assertEqual(len(response.data["ingredients"]), 1)
        self.assertEqual(response.data["ingredients"][0]["product"], "Сир")
        self.assertIn("instructions", response.data)

    def test_pending_recipe_not_available(self):
        response = self.client.get(reverse("recipe-detail", args=[self.hidden.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReferenceDataTests(CatalogTestCase):
    def test_categories_list(self):
        response = self.client.get(reverse("category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_diet_tags_list(self):
        response = self.client.get(reverse("diet-tag-list"))
        self.assertEqual(len(response.data), 2)

    def test_products_list(self):
        response = self.client.get(reverse("product-list"))
        self.assertEqual(response.data["count"], 2)
