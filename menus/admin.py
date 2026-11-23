from django.contrib import admin

from menus.models import Menu, MenuItem


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("user", "week_start", "status")
    inlines = [MenuItemInline]
