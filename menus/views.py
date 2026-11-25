from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from menus.models import Menu, MenuItem
from menus.serializers import MenuItemSerializer, MenuSerializer
from menus.services import build_shopping_list


class OwnMenuMixin:
    def get_menu(self):
        return get_object_or_404(Menu, pk=self.kwargs["pk"], user=self.request.user)


class MenuListCreateView(generics.ListCreateAPIView):
    serializer_class = MenuSerializer

    def get_queryset(self):
        queryset = Menu.objects.filter(user=self.request.user).prefetch_related(
            "items__recipe"
        )
        menu_status = self.request.query_params.get("status")
        if menu_status:
            queryset = queryset.filter(status=menu_status)
        return queryset


class MenuDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = MenuSerializer

    def get_queryset(self):
        return Menu.objects.filter(user=self.request.user).prefetch_related(
            "items__recipe"
        )


class MenuItemCreateView(OwnMenuMixin, generics.CreateAPIView):
    serializer_class = MenuItemSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["menu"] = self.get_menu()
        return context

    def perform_create(self, serializer):
        serializer.save(menu=self.get_menu())


class MenuItemDeleteView(OwnMenuMixin, generics.DestroyAPIView):
    def get_object(self):
        return get_object_or_404(
            MenuItem, pk=self.kwargs["item_id"], menu=self.get_menu()
        )


class MenuSaveView(OwnMenuMixin, APIView):
    def post(self, request, pk):
        menu = self.get_menu()

        if not menu.items.exists():
            return Response(
                {"detail": "Не можна зберегти порожнє меню."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        menu.status = Menu.Status.SAVED
        menu.save(update_fields=["status"])
        return Response(MenuSerializer(menu).data, status=status.HTTP_200_OK)


class ShoppingListView(OwnMenuMixin, APIView):
    def get(self, request, pk):
        menu = self.get_menu()
        menu_items = menu.items.select_related("recipe").prefetch_related(
            "recipe__ingredients__product"
        )
        return Response({"items": build_shopping_list(menu_items)})
