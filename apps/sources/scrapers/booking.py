from __future__ import annotations
import logging
import re
from datetime import date, timedelta

from .base import BaseScraper, ScrapedListing

logger = logging.getLogger(__name__)

_RATING_RE = re.compile(r"Scored\s+(\d+(?:\.\d+)?)")
_REVIEWS_RE = re.compile(r"([\d,]+)\s+reviews?")


class BookingScraper(BaseScraper):
    """
    Scrapes Booking.com's public search results page with a real
    headless browser — the results grid is populated client-side and
    plain HTTP requests get served an interstitial instead of listings.
    """

    source_type = "booking"
    _BASE_URL = "https://www.booking.com/searchresults.html"

    def fetch(self, check_in_offset_days: int = 7) -> list[ScrapedListing]:
        from urllib.parse import urlencode

        from bs4 import BeautifulSoup

        check_in = date.today() + timedelta(days=check_in_offset_days)
        check_out = check_in + timedelta(days=1)
        location = (
            f"{self.region.name}, {self.country.name}" if self.region else self.country.name
        )

        params = {
            "ss": location,
            "checkin": str(check_in),
            "checkout": str(check_out),
            "group_adults": 2,
            "no_rooms": 1,
            "selected_currency": "USD",
        }
        url = f"{self._BASE_URL}?{urlencode(params)}"

        try:
            html = self._fetch_rendered_html(url, wait_selector="[data-testid='property-card']")
        except Exception as exc:
            logger.error(f"BookingScraper failed for {self.region}: {exc}")
            return []

        soup = BeautifulSoup(html, "lxml")
        return self._parse_html(soup)

    def _parse_html(self, soup) -> list[ScrapedListing]:
        listings = []
        cards = soup.select("[data-testid='property-card']")
        for card in cards:
            try:
                title_el = card.select_one("[data-testid='title']")
                price_el = card.select_one("[data-testid='price-and-discounted-price']")
                rating_el = card.select_one("[data-testid='review-score']")
                link_el = card.select_one("a[data-testid='title-link']")

                if not title_el or not price_el:
                    continue

                price_text = price_el.get_text(strip=True).replace("$", "").replace(",", "")
                price_usd = float("".join(filter(lambda c: c.isdigit() or c == ".", price_text)) or 0)

                rating_text = rating_el.get_text("|", strip=True) if rating_el else ""
                rating_match = _RATING_RE.search(rating_text)
                rating = float(rating_match.group(1)) if rating_match else None
                reviews_match = _REVIEWS_RE.search(rating_text)
                reviews_count = int(reviews_match.group(1).replace(",", "")) if reviews_match else 0

                raw_href = link_el["href"] if link_el else ""
                href = raw_href.split("?")[0]
                listing_id = href.split("/")[-1].split(".")[0] if href else ""

                listings.append(ScrapedListing(
                    listing_id=listing_id,
                    title=title_el.get_text(strip=True),
                    price_usd=price_usd,
                    price_idr=None,
                    bedrooms=None,
                    bathrooms=None,
                    guests_capacity=None,
                    rating=rating,
                    reviews_count=reviews_count,
                    listing_url=href,
                    property_type="villa",
                    raw_data={"raw_html_title": title_el.get_text(strip=True)},
                ))
            except Exception as exc:
                logger.debug(f"Skipping booking card: {exc}")
        return listings
