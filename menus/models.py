from django.conf import settings
from django.db import models

from recipes.models import Recipe


class Menu(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        SAVED = "saved", "Збережене"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="menus"
    )
    week_start = models.DateField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_start"], name="unique_menu_per_week"
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.week_start}"


class MenuItem(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Сніданок"
        LUNCH = "lunch", "Обід"
        DINNER = "dinner", "Вечеря"
        SNACK = "snack", "Перекус"

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items")
    recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT, related_name="menu_items"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MealType.choices)

    class Meta:
        ordering = ["date", "meal_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["menu", "date", "meal_type"], name="unique_menu_slot"
            ),
        ]

    def __str__(self):
        return f"{self.date} {self.meal_type}: {self.recipe}"
