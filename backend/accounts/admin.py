from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccountSession, AccountToken, User, UserBlock


@admin.register(User)
class TableChatUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "public_id", "display_name", "email_verified_at", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Table Chat", {"fields": ("public_id", "display_name", "bio", "email_verified_at")}),)
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "public_id", "display_name", "password1", "password2")}),)


admin.site.register(AccountToken)
admin.site.register(AccountSession)
admin.site.register(UserBlock)
