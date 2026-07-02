from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_chat_id", "telegram_username", "preferred_region")
    search_fields = ("user__username", "telegram_chat_id", "telegram_username")
    raw_id_fields = ("user",)
