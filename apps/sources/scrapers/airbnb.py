from __future__ import annotations
import logging
import re
from datetime import date, timedelta
from urllib.parse import urlencode

from .base import BaseScraper, ScrapedListing

logger = logging.getLogger(__name__)

_PRICE_RE = re.compile(r"\$\s?([\d,]+)")
# Matches the rating only when immediately followed by "(<reviews>)", e.g.
# "4.79 (28)" — a bare `\d\.\d+` also matches unrelated figures like "2.5 baths".
_RATING_REVIEWS_RE = re.compile(r"(\d+\.\d+)\s*\((\d+)\)")


class AirbnbScraper(BaseScraper):
    """
    Scrapes Airbnb's public search results page with a real headless
    browser. Airbnb has no public API and blocks plain HTTP requests to
    its internal GraphQL endpoint without a signed session, so this
    renders the search page and parses listing cards instead. Selectors
    target `data-testid`/`itemprop` attributes, which drift less than
    Airbnb's generated CSS class names but can still change.
    """

    source_type = "airbnb"
    _BASE_URL = "https://www.airbnb.com/s/{location}/homes"

    def fetch(self, check_in_offset_days: int = 7) -> list[ScrapedListing]:
        from bs4 import BeautifulSoup

        check_in = date.today() + timedelta(days=check_in_offset_days)
        check_out = check_in + timedelta(days=1)
        location = (
            f"{self.region.name}, {self.country.name}" if self.region else self.country.name
        )
        location_path = location.replace(", ", "--").replace(" ", "-")

        params = urlencode({
            "checkin": str(check_in),
            "checkout": str(check_out),
            "adults": 2,
            "currency": "USD",
        })
        url = f"{self._BASE_URL.format(location=location_path)}?{params}"

        try:
            html = self._fetch_rendered_html(
                url,
                wait_selector="[data-testid='card-container']",
                scroll_steps=6,
            )
        except Exception as exc:
            logger.error(f"AirbnbScraper failed to load {url}: {exc}")
            return []

        soup = BeautifulSoup(html, "lxml")
        return self._parse_html(soup)

    def _parse_html(self, soup) -> list[ScrapedListing]:
        listings = []
        cards = soup.select("[data-testid='card-container']")
        for card in cards:
            try:
                link_el = card.select_one("a[href*='/rooms/']")
                if not link_el:
                    continue
                listing_id = link_el.get("href", "").split("/rooms/")[-1].split("?")[0]
                if not listing_id:
                    continue

                title_el = (
                    card.select_one("[data-testid='listing-card-name']")
                    or card.select_one("meta[itemprop='name']")
                )
                if title_el is not None and title_el.name == "meta":
                    title = title_el.get("content", "")
                elif title_el is not None:
                    title = title_el.get_text(strip=True)
                else:
                    title = ""

                card_text = card.get_text(" ", strip=True)
                price_match = _PRICE_RE.search(card_text)
                price_usd = float(price_match.group(1).replace(",", "")) if price_match else 0.0

                rating_reviews_match = _RATING_REVIEWS_RE.search(card_text)
                rating = float(rating_reviews_match.group(1)) if rating_reviews_match else None
                reviews_count = int(rating_reviews_match.group(2)) if rating_reviews_match else 0

                listings.append(ScrapedListing(
                    listing_id=listing_id,
                    title=title,
                    price_usd=price_usd,
                    price_idr=None,
                    bedrooms=None,
                    bathrooms=None,
                    guests_capacity=None,
                    rating=rating,
                    reviews_count=reviews_count,
                    listing_url=f"https://www.airbnb.com/rooms/{listing_id}",
                    raw_data={"card_text": card_text[:500]},
                ))
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug(f"Skipping airbnb card: {exc}")
        return listings
