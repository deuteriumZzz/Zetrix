import pytest
from django.urls import reverse

from tests.factories import CountryFactory, RegionFactory

pytestmark = pytest.mark.django_db


class TestRegionHierarchy:
    def test_region_can_have_a_parent(self):
        bali = RegionFactory(slug="bali", name="Bali", level="province", parent=None)
        canggu = RegionFactory(
            country=bali.country, slug="canggu-child", name="Canggu", level="city", parent=bali
        )
        assert canggu.parent == bali
        assert bali.children.filter(pk=canggu.pk).exists()

    def test_region_without_parent_is_top_level(self):
        region = RegionFactory(slug="standalone", name="Standalone", parent=None)
        assert region.parent is None


class TestGeoApi:
    def test_countries_list_is_public(self, api_client):
        CountryFactory()
        resp = api_client.get(reverse("api_v1:country-list"))
        assert resp.status_code == 200

    def test_country_detail_includes_nested_regions(self, api_client):
        region = RegionFactory(slug="canggu", name="Canggu")
        resp = api_client.get(
            reverse("api_v1:country-detail", args=[region.country.iso2])
        )
        assert resp.status_code == 200
        region_names = [r["name"] for r in resp.data["properties"]["regions"]]
        assert "Canggu" in region_names

    def test_regions_filterable_by_country(self, api_client):
        canggu = RegionFactory(slug="canggu", name="Canggu")
        other_country_region = RegionFactory(country=CountryFactory(iso2="TH", iso3="THA", name="Thailand"), slug="bangkok", name="Bangkok")
        resp = api_client.get(reverse("api_v1:region-list"), {"country": canggu.country.id})
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.data["results"]]
        assert str(canggu.id) in ids
        assert str(other_country_region.id) not in ids
