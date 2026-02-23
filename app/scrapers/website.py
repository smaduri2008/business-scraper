"""
Enhanced website scraper that extracts design and SEO elements.
"""
import re
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def scrape_website(url, timeout=10):
    """
    Scrape website for services, prices, team, and SEO/design elements.
    
    Returns dict with:
      - url, services, prices, team_members
      - meta_title, meta_description, h1_tags
      - images (with alt text), links, has_mobile_viewport
      - cta_buttons, text_length
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.error("Playwright not installed")
        return _empty_website_data(url)
    
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(timeout * 1000)
            
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)  # Wait for JS to load
            
            html = page.content()
            browser.close()
            
            return _parse_website_content(html, url)
            
    except Exception as exc:
        logger.error(f"Error scraping website {url}: {exc}")
        return _empty_website_data(url)


def _parse_website_content(html, url):
    """Parse HTML and extract all relevant data."""
    soup = BeautifulSoup(html, "html.parser")
    
    data = {
        "url": url,
        "services": _extract_services(soup),
        "prices": _extract_prices(soup),
        "team_members": _extract_team(soup),
        
        # SEO Elements
        "meta_title": _extract_meta_title(soup),
        "meta_description": _extract_meta_description(soup),
        "h1_tags": _extract_h1_tags(soup),
        
        # Design Elements
        "images": _extract_images(soup, url),
        "links": _extract_links(soup, url),
        "has_mobile_viewport": _check_mobile_viewport(soup),
        "cta_buttons": _extract_cta_buttons(soup),
        
        # Content Quality
        "text_length": len(soup.get_text(strip=True)),
    }
    
    return data


def _extract_meta_title(soup):
    """Extract page title."""
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else ""


def _extract_meta_description(soup):
    """Extract meta description."""
    meta = soup.find("meta", attrs={"name": "description"})
    return meta.get("content", "").strip() if meta else ""


def _extract_h1_tags(soup):
    """Extract all H1 tags."""
    h1_tags = soup.find_all("h1")
    return [h1.get_text(strip=True) for h1 in h1_tags if h1.get_text(strip=True)]


def _extract_images(soup, base_url):
    """Extract images with alt text info."""
    images = []
    for img in soup.find_all("img")[:50]:  # Limit to first 50
        src = img.get("src", "")
        alt = img.get("alt", "").strip()
        
        if src:
            # Convert relative URLs to absolute
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            
            images.append({
                "src": src,
                "alt": alt,
                "has_alt": bool(alt)
            })
    
    return images


def _extract_links(soup, base_url):
    """Extract internal links."""
    links = []
    base_domain = urlparse(base_url).netloc
    
    for a in soup.find_all("a", href=True)[:100]:  # Limit to first 100
        href = a.get("href", "")
        text = a.get_text(strip=True)
        
        if href:
            # Convert to absolute URL
            if not href.startswith("http"):
                href = urljoin(base_url, href)
            
            # Check if internal link
            link_domain = urlparse(href).netloc
            if link_domain == base_domain:
                links.append({
                    "url": href,
                    "text": text
                })
    
    return links


def _check_mobile_viewport(soup):
    """Check if mobile viewport meta tag exists."""
    viewport = soup.find("meta", attrs={"name": "viewport"})
    return viewport is not None


def _extract_cta_buttons(soup):
    """Extract call-to-action buttons/links."""
    cta_keywords = [
        "book", "schedule", "appointment", "contact", "call", "reserve",
        "get started", "sign up", "free consultation", "request", "order"
    ]
    
    cta_buttons = []
    
    # Check buttons
    for btn in soup.find_all(["button", "a"], class_=True):
        text = btn.get_text(strip=True).lower()
        if any(keyword in text for keyword in cta_keywords):
            cta_buttons.append(btn.get_text(strip=True))
    
    return list(set(cta_buttons))[:10]  # Unique, limit to 10


def _extract_services(soup):
    """Extract services from website."""
    services = []
    
    # Common service-related keywords
    service_keywords = [
        "service", "treatment", "procedure", "offering", "specialt"
    ]
    
    # Look for sections/headings related to services
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(strip=True).lower()
        if any(kw in text for kw in service_keywords):
            # Get nearby list items
            parent = heading.find_parent(["section", "div"])
            if parent:
                items = parent.find_all(["li", "p", "h4", "h5"])
                for item in items[:15]:
                    service_text = item.get_text(strip=True)
                    if 5 < len(service_text) < 100:
                        services.append(service_text)
    
    return list(set(services))[:20]  # Unique, limit to 20


def _extract_prices(soup):
    """Extract prices from website."""
    prices = []
    
    # Look for price patterns like $99, $1,500, etc.
    text = soup.get_text()
    price_pattern = r'\$[\d,]+(?:\.\d{2})?'
    
    for match in re.finditer(price_pattern, text):
        # Get context around price (50 chars before and after)
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].strip()
        
        prices.append({
            "price": match.group(),
            "context": context
        })
    
    return prices[:20]  # Limit to 20


def _extract_team(soup):
    """Extract team members from website."""
    team = []
    
    # Look for team/staff sections
    team_keywords = ["team", "staff", "doctor", "dr.", "provider", "specialist"]
    
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(strip=True).lower()
        if any(kw in text for kw in team_keywords):
            parent = heading.find_parent(["section", "div"])
            if parent:
                # Look for names with titles
                for elem in parent.find_all(["p", "h4", "h5", "li"]):
                    member_text = elem.get_text(strip=True)
                    
                    # Check if it looks like a name + title
                    if re.search(r'\b(MD|DDS|RN|NP|PA|DMD|DO)\b', member_text, re.I):
                        team.append(member_text)
                    elif 5 < len(member_text) < 100 and not member_text.startswith("$"):
                        team.append(member_text)
    
    return list(set(team))[:15]  # Unique, limit to 15


def _empty_website_data(url):
    """Return empty website data structure."""
    return {
        "url": url,
        "services": [],
        "prices": [],
        "team_members": [],
        "meta_title": "",
        "meta_description": "",
        "h1_tags": [],
        "images": [],
        "links": [],
        "has_mobile_viewport": False,
        "cta_buttons": [],
        "text_length": 0,
    }