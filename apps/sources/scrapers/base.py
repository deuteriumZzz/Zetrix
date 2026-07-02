from __future__ import annotations
import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

if TYPE_CHECKING:
    from apps.geo.models import Country, Region

logger = logging.getLogger(__name__)


@dataclass
class ScrapedListing:
    listing_id: str
    title: str
    price_usd: float
    price_idr: float | None
    bedrooms: int | None
    bathrooms: int | None
    guests_capacity: int | None
    rating: float | None
    reviews_count: int
    listing_url: str
    property_type: str = "villa"
    raw_data: dict = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class BaseScraper(abc.ABC):
    """
    Abstract scraper. All source scrapers must inherit from this class
    and implement the `fetch` method.

    Fetching is backed by a real headless Chromium instance (Playwright)
    rather than a plain HTTP client: target sites serve listings via
    client-side JS and block requests that don't look like a browser.
    """

    source_type: str = ""
    _USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    def __init__(self, country: "Country", region: "Region | None" = None, config: dict | None = None) -> None:
        self.country = country
        self.region = region
        self.config = config or {}
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    @property
    def location_label(self) -> str:
        """Human-readable place name for logging — used to build search queries."""
        return self.region.name if self.region else self.country.name

    @abc.abstractmethod
    def fetch(self, check_in_offset_days: int = 7) -> list[ScrapedListing]:
        """Fetch listings for the configured region."""
        ...

    def run(self, check_in_offset_days: int = 7) -> list[ScrapedListing]:
        """Entry point: fetch + basic validation."""
        logger.info(f"[{self.__class__.__name__}] Scraping {self.location_label}...")
        try:
            listings = self.fetch(check_in_offset_days=check_in_offset_days)
            valid = [l for l in listings if l.price_usd > 0]
            logger.info(f"[{self.__class__.__name__}] Got {len(valid)} valid listings")
            return valid
        except Exception:
            logger.exception(f"[{self.__class__.__name__}] Scraping failed for {self.location_label}")
            return []

    def _fetch_rendered_html(
        self,
        url: str,
        wait_selector: str | None = None,
        wait_timeout_ms: int = 15000,
        extra_wait_ms: int = 1500,
        scroll_steps: int = 0,
    ) -> str:
        """
        Navigate to `url` in the headless browser and return the rendered HTML.

        `scroll_steps` mouse-wheels down the page before capturing content —
        some result grids (e.g. Airbnb's) virtualize rows outside the
        viewport and only render them once scrolled into view.
        """
        if self._context is None:
            raise RuntimeError(
                f"{self.__class__.__name__} must be used as a context manager "
                "(e.g. `with scraper: ...`) before fetching pages."
            )

        page = self._context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=wait_timeout_ms)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=wait_timeout_ms)
                except Exception:
                    logger.warning(
                        f"[{self.__class__.__name__}] Selector '{wait_selector}' "
                        f"never appeared for {url}"
                    )
            page.wait_for_timeout(extra_wait_ms)
            for _ in range(scroll_steps):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(700)
            return page.content()
        finally:
            page.close()

    def __enter__(self) -> "BaseScraper":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._context = self._browser.new_context(
            user_agent=self._USER_AGENT,
            locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        return self

    def __exit__(self, *args) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
