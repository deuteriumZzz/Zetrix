from __future__ import annotations

import abc
import logging

logger = logging.getLogger(__name__)


class BaseIndexClient(abc.ABC):
    """One published index (Heritage Economic Freedom, Property Rights
    Alliance IPRI, OECD FDI Regulatory Restrictiveness, ...) used to ground
    the LLM's business-climate output. Real per-index clients (licensing/
    access terms not yet verified — see approved plan's open items) get
    registered via `register()`, same open/closed pattern as
    apps.sources.scrapers.ScraperFactory.
    """

    source_type: str = ""

    @abc.abstractmethod
    def fetch(self, country_iso3: str) -> dict | None:
        """Return this index's datapoints for a country, or None if the
        index doesn't cover it (e.g. OECD FDI only covers ~84 countries)."""
        ...


_REGISTRY: dict[str, type[BaseIndexClient]] = {}


def register(source_type: str, client_cls: type[BaseIndexClient]) -> None:
    _REGISTRY[source_type] = client_cls


def fetch_all_grounding(country_iso3: str) -> list[dict]:
    """Runs every registered index client for a country and returns the
    non-empty results as grounding context for the LLM prompt."""
    grounding = []
    for source_type, client_cls in _REGISTRY.items():
        try:
            result = client_cls().fetch(country_iso3)
        except Exception:
            logger.exception(f"Index client '{source_type}' failed for {country_iso3}")
            continue
        if result:
            grounding.append({"source": source_type, **result})
    return grounding
