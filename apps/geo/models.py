from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.core.models import BaseModel


class Continent(BaseModel):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Country(BaseModel):
    continent = models.ForeignKey(Continent, on_delete=models.PROTECT, related_name="countries")
    iso2 = models.CharField(max_length=2, unique=True)
    iso3 = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=150)
    centroid_lat = models.FloatField()
    centroid_lng = models.FloatField()
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)
    currency_code = models.CharField(max_length=3, blank=True)
    flag_emoji = models.CharField(max_length=8, blank=True)
    is_housing_supported = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self) -> str:
        return f"{self.name} ({self.iso2})"


class RegionLevel(models.TextChoices):
    PROVINCE = "province", "Province/State"
    CITY = "city", "City"
    NEIGHBORHOOD = "neighborhood", "Neighborhood"


class Region(BaseModel):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="regions")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    level = models.CharField(max_length=20, choices=RegionLevel.choices)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    centroid_lat = models.FloatField()
    centroid_lng = models.FloatField()
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["country", "name"]
        unique_together = ("country", "slug")

    def __str__(self) -> str:
        return f"{self.name}, {self.country.iso2}"
