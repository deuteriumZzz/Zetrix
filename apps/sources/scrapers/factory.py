from __future__ import annotations
from .base import BaseScraper
from .airbnb import AirbnbScraper
from .booking import BookingScraper

_REGISTRY: dict[str, type[BaseScraper]] = {
    "airbnb": AirbnbScraper,
    "booking": BookingScraper,
}


class ScraperFactory:
    """Instantiates the correct scraper by source_type string."""

    @classmethod
    def create(cls, source_type: str, country, region=None, config: dict | None = None) -> BaseScraper:
        scraper_cls = _REGISTRY.get(source_type)
        if scraper_cls is None:
            raise ValueError(
                f"Unknown source type: '{source_type}'. "
                f"Available: {list(_REGISTRY.keys())}"
            )
        return scraper_cls(country=country, region=region, config=config)

    @classmethod
    def register(cls, source_type: str, scraper_cls: type[BaseScraper]) -> None:
        """Register a new scraper at runtime (open/closed principle)."""
        _REGISTRY[source_type] = scraper_cls

    @classmethod
    def available_types(cls) -> list[str]:
        return list(_REGISTRY.keys())
