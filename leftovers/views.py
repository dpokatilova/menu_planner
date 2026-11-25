from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from leftovers.queries import find_suggestions, get_products_info
from leftovers.serializers import LeftoversResponseSerializer
from leftovers.services import calculate_leftovers
from menus.models import Menu
from menus.services import build_shopping_list


class LeftoversView(APIView):
    @extend_schema(responses=LeftoversResponseSerializer)
    def get(self, request, pk):
        menu = get_object_or_404(Menu, pk=pk, user=request.user)
        menu_items = list(
            menu.items.select_related("recipe").prefetch_related("recipe__ingredients__product")
        )

        shopping_items = build_shopping_list(menu_items)
        products_info = get_products_info([row["product_id"] for row in shopping_items])
        leftovers = calculate_leftovers(shopping_items, products_info)

        recipes_in_menu = {item.recipe_id for item in menu_items}
        for leftover in leftovers:
            leftover["suggestions"] = find_suggestions(
                leftover["product_id"], leftover["unit"], leftover["leftover"], recipes_in_menu
            )
        return Response({"leftovers": leftovers})
