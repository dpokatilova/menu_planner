from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Unit(models.TextChoices):
    GRAM = "g", "г"
    MILLILITER = "ml", "мл"
    PIECE = "pcs", "шт"


class Category(models.Model):
    class Kind(models.TextChoices):
        MEAL_TYPE = "meal_type", "Тип страви"
        CUISINE = "cuisine", "Кухня"

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class DietTag(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200, unique=True)
    is_packaged = models.BooleanField(default=False)
    package_size = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit = models.CharField(max_length=3, choices=Unit.choices, default=Unit.GRAM)
    shelf_life_days = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На перевірці"
        APPROVED = "approved", "Схвалено"
        REJECTED = "rejected", "Відхилено"

    class Source(models.TextChoices):
        USER = "user", "Користувач"
        MODERATOR = "moderator", "Модератор"
        IMPORTED = "imported", "Імпорт"

    title = models.CharField(max_length=200)
    title_lower = models.CharField(max_length=200, editable=False, db_index=True)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    cooking_time_min = models.PositiveIntegerField(null=True, blank=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    servings = models.PositiveSmallIntegerField(default=1)

    categories = models.ManyToManyField(Category, blank=True, related_name="recipes")
    diet_tags = models.ManyToManyField(DietTag, blank=True, related_name="recipes")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.USER)
    external_id = models.CharField(max_length=100, blank=True)
    ai_enriched = models.BooleanField(default=False)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recipes",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_recipes",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                condition=~Q(external_id=""),
                name="unique_source_external_id",
            ),
        ]

    def save(self, *args, **kwargs):
        self.title_lower = self.title.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="recipe_ingredients"
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit = models.CharField(max_length=3, choices=Unit.choices)

    def __str__(self):
        return f"{self.product} {self.amount} {self.unit}"
