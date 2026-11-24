import django_filters

from recipes.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    category = django_filters.CharFilter(field_name="categories__slug")
    diet_tag = django_filters.CharFilter(method="filter_diet_tags")
    product = django_filters.NumberFilter(field_name="ingredients__product_id")
    max_time = django_filters.NumberFilter(field_name="cooking_time_min", lookup_expr="lte")
    max_calories = django_filters.NumberFilter(field_name="calories", lookup_expr="lte")

    class Meta:
        model = Recipe
        fields = []

    @property
    def qs(self):
        return super().qs.distinct()

    def filter_search(self, queryset, name, value):
        return queryset.filter(title_lower__contains=value.lower())

    def filter_diet_tags(self, queryset, name, value):
        for slug in value.split(","):
            slug = slug.strip()
            if slug:
                queryset = queryset.filter(diet_tags__slug=slug)
        return queryset
