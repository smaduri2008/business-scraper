"""
Google Maps scraper using Playwright.
"""
import re
import logging
from app.scrapers.utils import random_delay, clean_text

logger = logging.getLogger(__name__)

# Maximum time (ms) to wait for page elements
DEFAULT_TIMEOUT = 15000


def scrape_google_maps(niche, location, max_results=10):
    """
    Scrape businesses from Google Maps for a given niche and location.

    Returns a list of business dictionaries containing:
      name, rating, reviews_count, address, phone, website, hours
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.error("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        return []

    results = []
    query = f"{niche} in {location}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT)

            url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            logger.info("Navigating to: %s", url)
            page.goto(url, wait_until="domcontentloaded")

            # Wait for the results panel
            try:
                page.wait_for_selector('[role="feed"]', timeout=DEFAULT_TIMEOUT)
            except PWTimeout:
                logger.warning("Results feed not found for query: %s", query)
                browser.close()
                return []

            # Scroll to load more results
            feed = page.query_selector('[role="feed"]')
            if feed:
                for _ in range(max(1, max_results // 5)):
                    page.evaluate("(el) => el.scrollBy(0, 1000)", feed)
                    random_delay(1.0, 1.5)

            # Collect listing links
            listings = page.query_selector_all('a[href*="/maps/place/"]')
            logger.info("Found %d listing links", len(listings))

            seen_hrefs = set()
            for listing in listings:
                if len(results) >= max_results:
                    break

                href = listing.get_attribute("href") or ""
                if href in seen_hrefs:
                    continue
                seen_hrefs.add(href)

                try:
                    listing.click()
                    random_delay()

                    business = _extract_business_details(page)
                    if business.get("name"):
                        results.append(business)
                        logger.info("Scraped: %s", business.get("name"))
                except Exception as exc:
                    logger.warning("Error clicking listing: %s", exc)

            browser.close()
    except Exception as exc:
        logger.error("Google Maps scraper error: %s", exc)

    return results


def _extract_business_details(page):
    """Extract details from an open Google Maps business panel."""
    try:
        from playwright.sync_api import TimeoutError as PWTimeout
    except ImportError:
        return {}

    business = {}

    # Wait briefly for the detail panel to load
    try:
        page.wait_for_selector('h1', timeout=8000)
    except Exception:
        pass

    # Name
    name_el = page.query_selector("h1")
    business["name"] = clean_text(name_el.inner_text()) if name_el else ""

    # Rating
    try:
        rating_el = page.query_selector('[jsaction*="pane.rating"]') or \
                    page.query_selector('span[aria-label*="stars"]')
        if rating_el:
            text = rating_el.get_attribute("aria-label") or rating_el.inner_text()
            m = re.search(r"([\d.]+)", text)
            business["rating"] = float(m.group(1)) if m else None
        else:
            business["rating"] = None
    except Exception:
        business["rating"] = None

    # Reviews count
    try:
        reviews_el = page.query_selector('button[jsaction*="reviewChart"]') or \
                     page.query_selector('span[aria-label*="review"]')
        if reviews_el:
            text = reviews_el.inner_text()
            m = re.search(r"([\d,]+)", text)
            business["reviews_count"] = int(m.group(1).replace(",", "")) if m else None
        else:
            business["reviews_count"] = None
    except Exception:
        business["reviews_count"] = None

    # Address, phone, website, hours — extracted from info buttons/links
    info_buttons = page.query_selector_all('button[data-item-id], a[data-item-id]')
    for btn in info_buttons:
        item_id = btn.get_attribute("data-item-id") or ""
        text = clean_text(btn.inner_text())
        href = btn.get_attribute("href") or ""

        if "address" in item_id:
            business["address"] = text
        elif "phone" in item_id:
            business["phone"] = text
        elif "authority" in item_id or href.startswith("http"):
            if href and "google.com" not in href and "maps" not in href:
                business["website"] = href

    # Hours (aria-label on hours button)
    hours_btn = page.query_selector('button[data-item-id*="oh"]')
    if hours_btn:
        business["hours"] = clean_text(hours_btn.get_attribute("aria-label") or hours_btn.inner_text())

    # Fill missing keys
    for key in ("address", "phone", "website", "hours"):
        business.setdefault(key, None)

    return business
