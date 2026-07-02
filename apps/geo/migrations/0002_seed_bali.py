from django.db import migrations


BALI_SUB_REGIONS = [
    ("canggu", "Canggu", -8.6478, 115.1385),
    ("ubud", "Ubud", -8.5069, 115.2625),
    ("kuta", "Kuta", -8.7186, 115.1686),
    ("seminyak", "Seminyak", -8.6907, 115.1553),
    ("nusa_dua", "Nusa Dua", -8.8005, 115.2270),
    ("uluwatu", "Uluwatu", -8.8290, 115.0849),
]


def seed_bali(apps, schema_editor):
    Continent = apps.get_model("geo", "Continent")
    Country = apps.get_model("geo", "Country")
    Region = apps.get_model("geo", "Region")

    asia, _ = Continent.objects.get_or_create(code="AS", defaults={"name": "Asia", "slug": "asia"})
    indonesia, _ = Country.objects.get_or_create(
        iso2="ID",
        defaults={
            "iso3": "IDN",
            "name": "Indonesia",
            "continent": asia,
            "centroid_lat": -5.0,
            "centroid_lng": 120.0,
            "currency_code": "IDR",
            "is_housing_supported": True,
        },
    )
    if not indonesia.is_housing_supported:
        indonesia.is_housing_supported = True
        indonesia.save(update_fields=["is_housing_supported"])

    bali, _ = Region.objects.get_or_create(
        country=indonesia,
        slug="bali",
        defaults={
            "parent": None,
            "level": "province",
            "name": "Bali",
            "centroid_lat": -8.3405,
            "centroid_lng": 115.0920,
        },
    )

    for slug, name, lat, lng in BALI_SUB_REGIONS:
        Region.objects.get_or_create(
            country=indonesia,
            slug=slug,
            defaults={
                "parent": bali,
                "level": "city",
                "name": name,
                "centroid_lat": lat,
                "centroid_lng": lng,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_bali, noop),
    ]
