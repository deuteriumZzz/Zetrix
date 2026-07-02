from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "username", "email",
            "telegram_chat_id", "telegram_username",
            "preferred_country", "preferred_region", "preferred_market_type",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "username", "email", "created_at", "updated_at")
