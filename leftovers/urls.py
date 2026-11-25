from django.urls import path

from leftovers.views import LeftoversView

urlpatterns = [
    path("menus/<int:pk>/leftovers/", LeftoversView.as_view(), name="menu-leftovers"),
]
