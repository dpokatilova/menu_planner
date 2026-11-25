from django.urls import path

from menus.views import MenuDetailView, MenuItemCreateView, MenuItemDeleteView, MenuListCreateView, MenuSaveView, ShoppingListView

urlpatterns = [
    path("menus/", MenuListCreateView.as_view(), name="menu-list"),
    path("menus/<int:pk>/", MenuDetailView.as_view(), name="menu-detail"),
    path("menus/<int:pk>/items/", MenuItemCreateView.as_view(), name="menu-item-create"),
    path(
        "menus/<int:pk>/items/<int:item_id>/",
        MenuItemDeleteView.as_view(),
        name="menu-item-delete",
    ),
    path("menus/<int:pk>/save/", MenuSaveView.as_view(), name="menu-save"),
path(
        "menus/<int:pk>/shopping-list/",
        ShoppingListView.as_view(),
        name="menu-shopping-list",
    ),
]
