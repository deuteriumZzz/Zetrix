import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pass12345")


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="bob", password="pass12345")


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_user(
        username="admin", password="pass12345", is_staff=True, is_superuser=True
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
