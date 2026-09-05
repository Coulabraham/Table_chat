from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class TableChatUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "chess_level", "is_staff")
    fieldsets = ((None, {"fields": ("email", "password")}), ("Profil", {"fields": ("display_name", "chess_level")}), ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}), ("Dates", {"fields": ("last_login", "date_joined")}))
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "display_name", "password1", "password2")}),)
    search_fields = ("email", "display_name")

