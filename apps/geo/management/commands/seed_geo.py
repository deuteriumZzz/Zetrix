from __future__ import annotations

import json
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.geo.models import Continent, Country

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# mledoze/countries "region" -> our Continent code/name.
REGION_MAP = {
    "Africa": ("AF", "Africa"),
    "Americas": ("AM", "Americas"),
    "Antarctic": ("AN", "Antarctica"),
    "Asia": ("AS", "Asia"),
    "Europe": ("EU", "Europe"),
    "Oceania": ("OC", "Oceania"),
}


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace("'", "")


class Command(BaseCommand):
    """Seeds all UN-member countries + continents from a bundled static dataset.

    Data is read from apps/geo/data/{countries.json,world_boundaries.geojson}
    (mledoze/countries + Natural Earth 110m admin-0 boundaries), not a live
    external API, so seeding is reproducible/offline-safe.
    """

    help = "Seed Continent/Country rows for all ~195 UN-member states."

    @transaction.atomic
    def handle(self, *args, **options):
        countries_raw = json.loads((DATA_DIR / "countries.json").read_text())
        boundaries_raw = json.loads((DATA_DIR / "world_boundaries.geojson").read_text())

        boundary_by_iso2 = {}
        for feature in boundaries_raw["features"]:
            iso2 = feature["properties"].get("ISO_A2")
            if not iso2 or iso2 == "-99":
                continue
            geom = GEOSGeometry(json.dumps(feature["geometry"]))
            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)
            boundary_by_iso2[iso2] = geom

        continents = {}
        for code, name in REGION_MAP.values():
            continents[code], _ = Continent.objects.update_or_create(
                code=code, defaults={"name": name, "slug": _slugify(name)}
            )

        created, updated = 0, 0
        for entry in countries_raw:
            if not entry.get("unMember"):
                continue
            region = entry.get("region")
            if region not in REGION_MAP:
                continue
            code, _ = REGION_MAP[region]
            iso2 = entry["cca2"]
            iso3 = entry["cca3"]
            name = entry["name"]["common"]
            latlng = entry.get("latlng") or [0.0, 0.0]
            currencies = entry.get("currencies") or {}
            currency_code = next(iter(currencies), "")

            _, was_created = Country.objects.update_or_create(
                iso2=iso2,
                defaults={
                    "iso3": iso3,
                    "name": name,
                    "continent": continents[code],
                    "centroid_lat": latlng[0],
                    "centroid_lng": latlng[1],
                    "currency_code": currency_code,
                    "flag_emoji": entry.get("flag", ""),
                    "boundary": boundary_by_iso2.get(iso2),
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(continents)} continents, {created} new / {updated} "
            f"updated countries ({len(boundary_by_iso2)} with boundary polygons)."
        ))
