"""
Shared scraper utilities.
"""
import re
import logging
import time
import random

logger = logging.getLogger(__name__)


def random_delay(min_seconds=1.5, max_seconds=2.5):
    """Sleep for a random duration to avoid rate limiting."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def extract_prices(text):
    """Extract price strings from raw text using a dollar-amount regex."""
    pattern = r"\$\s*\d+(?:,\d{3})*(?:\.\d{2})?"
    return re.findall(pattern, text)


def clean_text(text):
    """Strip excess whitespace from a string."""
    if not text:
        return ""
    return " ".join(text.split())


def extract_instagram_username_from_url(url):
    """Parse an Instagram username out of a profile URL."""
    match = re.search(r"instagram\.com/([^/?#]+)", url or "")
    if match:
        username = match.group(1).strip("/")
        # Ignore generic paths
        if username.lower() not in ("p", "explore", "accounts", "reel", "stories"):
            return username
    return None


def generate_instagram_usernames(business_name):
    """Generate plausible Instagram username candidates from a business name."""
    base = re.sub(r"[^a-zA-Z0-9]", "", business_name.lower())
    candidates = [base]
    # Try removing common words
    short = re.sub(r"(the|a|an|and|or|of|in|at|for|llc|inc|co|corp)", "", base)
    if short and short != base:
        candidates.append(short)
    # First 20 chars
    if len(base) > 20:
        candidates.append(base[:20])
    return candidates
