"""
Website scraper using Playwright + BeautifulSoup.
"""
import re
import logging
from urllib.parse import urlparse
from app.scrapers.utils import random_delay, clean_text, extract_prices

logger = logging.getLogger(__name__)

TITLE_KEYWORDS = re.compile(
    r"\b(MD|DO|DDS|DMD|RN|NP|PA|PhD|PT|OT|DC|LAc|LCSW|MBA|Esq|CPA|CFP)\b", re.IGNORECASE
)

DEFAULT_TIMEOUT = 15000


def scrape_website(url):
    """
    Scrape a business website for services, prices, team members, and social links.

    Returns a dictionary with:
      services, prices, team_members, instagram_url, raw_text
    """
    if not url:
        return {}

    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("Playwright or BeautifulSoup is not installed.")
        return {}

    result = {
        "services": [],
        "prices": [],
        "team_members": [],
        "instagram_url": None,
        "raw_text": "",
    }

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT)

            logger.info("Scraping website: %s", url)
            page.goto(url, wait_until="domcontentloaded")
            random_delay()

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

        # Extract raw visible text
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        raw_text = clean_text(soup.get_text(separator=" "))
        result["raw_text"] = raw_text[:5000]  # cap to 5k chars for AI analysis

        # Extract prices
        result["prices"] = list(set(extract_prices(raw_text)))

        # Find Instagram link
        for a in soup.find_all("a", href=True):
            href = a["href"]
            try:
                hostname = urlparse(href).hostname or ""
                if hostname == "instagram.com" or hostname.endswith(".instagram.com"):
                    result["instagram_url"] = href
                    break
            except Exception:
                pass

        # Extract services from lists and headings
        result["services"] = _extract_services(soup)

        # Extract team members
        result["team_members"] = _extract_team_members(soup)

    except Exception as exc:
        logger.error("Website scraper error for %s: %s", url, exc)

    return result


def _extract_services(soup):
    """Heuristically find service names from the page."""
    services = []
    seen = set()

    # Look for elements with service-related class/id names
    for tag in soup.find_all(True):
        classes = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        combined = (classes + " " + tag_id).lower()
        if any(kw in combined for kw in ("service", "treatment", "menu", "offer", "procedure")):
            for li in tag.find_all("li"):
                text = clean_text(li.get_text())
                if text and text not in seen and len(text) < 100:
                    services.append(text)
                    seen.add(text)

    # Fallback: look for list items under headings that mention services
    if not services:
        for heading in soup.find_all(re.compile("^h[2-4]$")):
            heading_text = heading.get_text().lower()
            if any(kw in heading_text for kw in ("service", "treatment", "what we", "our offer")):
                sibling = heading.find_next_sibling()
                if sibling and sibling.name in ("ul", "ol"):
                    for li in sibling.find_all("li"):
                        text = clean_text(li.get_text())
                        if text and text not in seen and len(text) < 100:
                            services.append(text)
                            seen.add(text)

    return services[:20]


def _extract_team_members(soup):
    """Heuristically find team member names and titles from the page."""
    members = []
    seen = set()

    # Look for team/staff/about sections
    for tag in soup.find_all(True):
        classes = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        combined = (classes + " " + tag_id).lower()
        if any(kw in combined for kw in ("team", "staff", "doctor", "provider", "about", "meet")):
            for child in tag.find_all(["h2", "h3", "h4", "p", "span"]):
                text = clean_text(child.get_text())
                if TITLE_KEYWORDS.search(text) and text not in seen and len(text) < 100:
                    members.append(text)
                    seen.add(text)

    return members[:10]
