from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Continent, Country, Region


@admin.register(Continent)
class ContinentAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Country)
class CountryAdmin(GISModelAdmin):
    list_display = ("name", "iso2", "iso3", "continent", "is_housing_supported")
    list_filter = ("continent", "is_housing_supported")
    search_fields = ("name", "iso2", "iso3")


@admin.register(Region)
class RegionAdmin(GISModelAdmin):
    list_display = ("name", "country", "level", "parent")
    list_filter = ("country", "level")
    search_fields = ("name",)
