from django.urls import path
from .views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    UserProfileView,
)

urlpatterns = [
    path("me/", UserProfileView.as_view(), name="user-profile"),
    path("register/", RegisterView.as_view(), name="user-register"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
