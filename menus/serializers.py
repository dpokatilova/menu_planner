from datetime import timedelta

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from menus.models import Menu, MenuItem
from recipes.models import Recipe


class MenuItemSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.filter(status=Recipe.Status.APPROVED)
    )
    recipe_title = serializers.CharField(source="recipe.title", read_only=True)

    class Meta:
        model = MenuItem
        fields = ("id", "recipe", "recipe_title", "date", "meal_type")

    def validate(self, attrs):
        menu = self.context["menu"]
        date = attrs["date"]

        week_end = menu.week_start + timedelta(days=6)
        if not menu.week_start <= date <= week_end:
            raise serializers.ValidationError(
                {"date": f"Дата має бути між {menu.week_start} і {week_end}."}
            )

        taken = MenuItem.objects.filter(
            menu=menu, date=date, meal_type=attrs["meal_type"]
        ).exists()
        if taken:
            raise serializers.ValidationError(
                "На цей день і прийом їжі вже є рецепт."
            )

        return attrs


class MenuSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = ("id", "user", "week_start", "status", "items", "created_at")
        read_only_fields = ("status", "created_at")
        validators = [
            UniqueTogetherValidator(
                queryset=Menu.objects.all(),
                fields=("user", "week_start"),
                message="Меню на цей тиждень уже існує.",
            )
        ]

    def validate_week_start(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError("Тиждень має починатися з понеділка.")
        return value
