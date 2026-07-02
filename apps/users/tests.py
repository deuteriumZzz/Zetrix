import pytest
from django.urls import reverse

from apps.users.models import UserProfile
from tests.factories import RegionFactory

pytestmark = pytest.mark.django_db


class TestUserProfileView:
    def test_requires_auth(self, api_client):
        resp = api_client.get(reverse("api_v1:user-profile"))
        assert resp.status_code == 401

    def test_get_creates_profile_on_first_access(self, auth_client, user):
        assert not UserProfile.objects.filter(user=user).exists()
        resp = auth_client.get(reverse("api_v1:user-profile"))
        assert resp.status_code == 200
        assert resp.data["username"] == user.username
        assert UserProfile.objects.filter(user=user).exists()

    def test_patch_updates_own_profile(self, auth_client):
        region = RegionFactory(slug="canggu", name="Canggu")
        auth_client.get(reverse("api_v1:user-profile"))  # vivify
        resp = auth_client.patch(
            reverse("api_v1:user-profile"), {"preferred_region": str(region.id)}
        )
        assert resp.status_code == 200
        assert resp.data["preferred_region"] == region.id

    def test_email_and_username_are_read_only(self, auth_client, user):
        resp = auth_client.patch(
            reverse("api_v1:user-profile"), {"username": "hacker", "email": "x@x.com"}
        )
        assert resp.status_code == 200
        assert resp.data["username"] == user.username
