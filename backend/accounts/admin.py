from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class TableChatUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "public_id", "display_name", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Table Chat", {"fields": ("public_id", "display_name", "bio")}),)
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "public_id", "display_name", "password1", "password2")}),)

