"""
Single-URL brand audit endpoint.

POST /api/audit
  Body: { "url": "https://example.com" }

Returns brand info, website data, website grade, and AI audit sections.
"""
import logging
from urllib.parse import urlparse, urlunparse

from flask import Blueprint, request, jsonify
from bs4 import BeautifulSoup

from app.scrapers.website import scrape_website, extract_brand_info
from app.analyzers.website_grader import grade_website
from app.analyzers.brand_auditor import generate_brand_audit

logger = logging.getLogger(__name__)
audit_bp = Blueprint("audit", __name__)


def _normalize_url(raw: str) -> str | None:
    """
    Normalise a user-supplied URL string.

    - Strips whitespace.
    - Prepends https:// if no scheme is present.
    - Validates that the scheme is http or https and a netloc exists.

    Returns the normalised URL string, or None if the URL is invalid.
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    # Try to parse as-is first to detect an explicit non-http/https scheme
    try:
        parsed_raw = urlparse(raw)
    except Exception:
        return None

    if parsed_raw.scheme and parsed_raw.scheme not in ("http", "https"):
        # Explicit unsupported scheme (e.g., ftp://, mailto:)
        return None

    # Prepend scheme if missing (no scheme or relative-style)
    if not parsed_raw.scheme:
        raw = "https://" + raw

    try:
        parsed = urlparse(raw)
    except Exception:
        return None

    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None

    # Reconstruct a clean URL (drop fragment, keep path/query)
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))
    return normalized


@audit_bp.route("/audit", methods=["POST"])
def audit():
    """
    Brand audit for a single website URL.

    Request JSON:
        { "url": "https://example.com" }

    Response JSON:
        {
          "url": <original input>,
          "normalized_url": <cleaned URL>,
          "brand": { name, phones, emails, addresses, socials },
          "website_data": { ...scraped fields... },
          "website_grade": { ...existing grade object... },
          "audit": { brand_summary, positioning_guess, conversion_notes, top_recommendations }
        }
    """
    body = request.get_json(silent=True) or {}
    raw_url = body.get("url", "")

    normalized = _normalize_url(raw_url)
    if not normalized:
        return jsonify({
            "error": "Invalid URL. Please provide a valid http or https URL.",
            "url": raw_url,
        }), 422

    logger.info("Brand audit requested for %s", normalized)

    # ── 1. Scrape website ──────────────────────────────────────────────────
    try:
        website_data = scrape_website(normalized) or {}
    except Exception as exc:
        logger.error("Website scrape failed for %s: %s", normalized, exc)
        return jsonify({
            "error": "Failed to load the website. It may be unreachable or blocking automated access.",
            "url": raw_url,
            "normalized_url": normalized,
        }), 502

    # ── 2. Extract brand info from the raw HTML ────────────────────────────
    # Re-parse the already-fetched HTML so we don't need a second network call.
    # scrape_website() returns structured data, not the raw HTML.
    # We call extract_brand_info with a lightweight stub if no HTML is available.
    try:
        brand_info = _extract_brand_from_website_data(website_data, normalized)
    except Exception as exc:
        logger.warning("Brand extraction failed for %s: %s", normalized, exc)
        brand_info = {"name": "", "phones": [], "emails": [], "addresses": [], "socials": {}}

    # ── 3. Grade website ───────────────────────────────────────────────────
    try:
        website_grade = grade_website(website_data)
    except Exception as exc:
        logger.error("Website grading failed for %s: %s", normalized, exc)
        return jsonify({
            "error": "Website grading service temporarily unavailable.",
            "url": raw_url,
            "normalized_url": normalized,
        }), 500

    # ── 4. AI brand audit ──────────────────────────────────────────────────
    try:
        audit_result = generate_brand_audit(website_data, brand_info)
    except Exception as exc:
        logger.error("Brand audit AI failed for %s: %s", normalized, exc)
        return jsonify({
            "error": "AI analysis service temporarily unavailable.",
            "url": raw_url,
            "normalized_url": normalized,
        }), 500

    # ── 5. Build response ──────────────────────────────────────────────────
    # Strip bulky images/links arrays from website_data to keep response lean
    website_data_response = {
        k: v for k, v in website_data.items()
        if k not in ("images", "links")
    }
    website_data_response["images_count"] = len(website_data.get("images", []))
    website_data_response["images_with_alt"] = sum(
        1 for img in website_data.get("images", []) if img.get("has_alt")
    )
    website_data_response["internal_links_count"] = len(website_data.get("links", []))

    return jsonify({
        "url": raw_url,
        "normalized_url": normalized,
        "brand": brand_info,
        "website_data": website_data_response,
        "website_grade": website_grade,
        "audit": audit_result,
    })


def _extract_brand_from_website_data(website_data: dict, url: str) -> dict:
    """
    Build brand info from already-extracted website_data fields.

    Since scrape_website() doesn't return raw HTML we reconstruct a minimal
    BeautifulSoup stub from the structured data, and also pull social links
    found in the links list.
    """
    from app.scrapers.website import (
        _SOCIAL_PATTERNS, _PHONE_RE, _EMAIL_RE, _ADDRESS_RE,
    )

    # --- Brand name ----------------------------------------------------------
    name = ""
    meta_title = website_data.get("meta_title", "")
    if meta_title:
        name = meta_title.split("|")[0].split("–")[0].split("-")[0].strip()
    if not name and website_data.get("h1_tags"):
        name = website_data["h1_tags"][0]

    # --- Social links from internal links ------------------------------------
    socials: dict = {}
    for link in website_data.get("links", []):
        href = link.get("url", "")
        for platform, pattern in _SOCIAL_PATTERNS.items():
            if platform not in socials and platform in href:
                m = pattern.search(href)
                if m:
                    socials[platform] = href.split("?")[0]
                    break

    # --- Phones & emails from CTA button text and service text ---------------
    # We synthesise a text blob from structured fields
    text_blob = " ".join([
        meta_title,
        website_data.get("meta_description", ""),
        " ".join(website_data.get("h1_tags", [])),
        " ".join(website_data.get("services", [])),
        " ".join(website_data.get("cta_buttons", [])),
    ])

    phones = list(dict.fromkeys(_PHONE_RE.findall(text_blob)))[:5]
    emails = [
        e for e in dict.fromkeys(_EMAIL_RE.findall(text_blob))
        if not e.endswith((".png", ".jpg", ".gif", ".svg"))
    ][:5]
    addresses = list(dict.fromkeys(_ADDRESS_RE.findall(text_blob)))[:3]

    return {
        "name": name,
        "phones": phones,
        "emails": emails,
        "addresses": addresses,
        "socials": socials,
    }
