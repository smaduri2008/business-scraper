"""
API routes for the business intelligence scraper.
"""
import json
import logging
import os
import time
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.analyzers.ai_analyzer import analyze_business
from app.database import get_session
from app.models import Analysis, Business, InstagramData
from app.scrapers.google_maps import scrape_google_maps
from app.scrapers.instagram import scrape_instagram
from app.scrapers.website import scrape_website

logger = logging.getLogger(__name__)

analyze_bp = Blueprint("analyze", __name__)

# Path to the niche config file
_NICHES_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "niches", "config.json")


def _load_niches():
    """Load and return the niche configuration dictionary."""
    try:
        with open(_NICHES_CONFIG_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to load niches config: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@analyze_bp.route("/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


# ---------------------------------------------------------------------------
# Niches listing
# ---------------------------------------------------------------------------

@analyze_bp.route("/niches", methods=["GET"])
def list_niches():
    """Return available niche configurations."""
    niches = _load_niches()
    return jsonify(
        {
            key: {
                "label": cfg.get("label", key),
                "common_services": cfg.get("common_services", []),
            }
            for key, cfg in niches.items()
            if key != "default"
        }
    )


# ---------------------------------------------------------------------------
# Main analysis endpoint
# ---------------------------------------------------------------------------

@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyse businesses for a given niche and location.

    Request body (JSON):
        {
            "niche": "medspas",
            "location": "Miami, FL",
            "max_results": 10
        }
    """
    body = request.get_json(silent=True) or {}

    niche = (body.get("niche") or "").strip()
    location = (body.get("location") or "").strip()
    max_results = int(body.get("max_results", 10))

    # --- Input validation ---
    if not niche:
        return jsonify({"error": "niche is required"}), 400
    if not location:
        return jsonify({"error": "location is required"}), 400
    if max_results < 1 or max_results > 50:
        return jsonify({"error": "max_results must be between 1 and 50"}), 400

    niches_config = _load_niches()
    niche_cfg = niches_config.get(niche) or niches_config.get("default", {})

    start_time = time.time()
    businesses_output = []

    # 1. Scrape Google Maps
    logger.info("Scraping Google Maps: niche=%s location=%s max=%d", niche, location, max_results)
    try:
        raw_businesses = scrape_google_maps(niche, location, max_results)
    except Exception as exc:
        logger.error("Google Maps scraper failed: %s", exc)
        raw_businesses = []

    session = get_session()

    for raw in raw_businesses:
        business_result = dict(raw)
        business_result["niche"] = niche
        business_result["location"] = location

        # 2. Scrape website
        website_data = {}
        if raw.get("website"):
            try:
                website_data = scrape_website(raw["website"]) or {}
            except Exception as exc:
                logger.error("Website scraper failed for %s: %s", raw.get("website"), exc)

        business_result["services"] = website_data.get("services", [])
        business_result["prices"] = website_data.get("prices", [])
        business_result["team_members"] = website_data.get("team_members", [])

        # 2.5 Grade website
        website_grade = {}
        if website_data:
            try:
                from app.analyzers.website_grader import grade_website
                website_grade = grade_website(website_data)
            except Exception as exc:
                logger.error("Website grading failed for %s: %s", raw.get("website"), exc)
        
        business_result["website_grade"] = website_grade

        # 3. Scrape Instagram
        ig_data = None
        try:
            ig_data = scrape_instagram(
                raw.get("name", ""),
                website_data.get("instagram_url"),
            )
        except Exception as exc:
            logger.error("Instagram scraper failed for %s: %s", raw.get("name"), exc)

        business_result["instagram"] = ig_data

        # 4. AI analysis
        analysis_result = {}
        try:
            analysis_result = analyze_business(business_result, niche)
        except Exception as exc:
            logger.error("AI analysis failed for %s: %s", raw.get("name"), exc)

        business_result["analysis"] = analysis_result

        # 5. Persist to database
        try:
            _save_to_db(session, business_result, ig_data, analysis_result)
        except Exception as exc:
            logger.error("DB save failed for %s: %s", raw.get("name"), exc)
            session.rollback()

        businesses_output.append(business_result)

    elapsed = round(time.time() - start_time, 2)

    return jsonify(
        {
            "niche": niche,
            "location": location,
            "results_count": len(businesses_output),
            "processing_time_seconds": elapsed,
            "businesses": businesses_output,
        }
    )


# ---------------------------------------------------------------------------
# DB persistence helper
# ---------------------------------------------------------------------------

def _save_to_db(session, business_data, ig_data, analysis_data):
    """Persist a scraped business and its related data to the database."""
    business = Business(
        name=business_data.get("name", ""),
        niche=business_data.get("niche"),
        location=business_data.get("location"),
        website=business_data.get("website"),
        phone=business_data.get("phone"),
        address=business_data.get("address"),
        rating=business_data.get("rating"),
        reviews_count=business_data.get("reviews_count"),
        hours=business_data.get("hours"),
        scraped_at=datetime.utcnow(),
    )
    session.add(business)
    session.flush()  # get the generated ID

    if ig_data:
        ig = InstagramData(
            business_id=business.id,
            username=ig_data.get("username"),
            followers=ig_data.get("followers"),
            following=ig_data.get("following"),
            posts=ig_data.get("posts"),
            engagement_rate=ig_data.get("engagement_rate"),
            bio=ig_data.get("bio"),
            is_verified=ig_data.get("is_verified", False),
            is_business=ig_data.get("is_business", False),
        )
        session.add(ig)

    if analysis_data:
        analysis = Analysis(
            business_id=business.id,
            revenue_streams=json.dumps(analysis_data.get("revenue_streams", [])),
            estimated_revenue_tier=analysis_data.get("estimated_revenue_tier"),
            pricing_strategy=analysis_data.get("pricing_strategy"),
            service_quality_score=analysis_data.get("service_quality_score"),
            competitive_assessment=analysis_data.get("competitive_assessment"),
            niche_specific_insights=analysis_data.get("niche_specific_insights"),
        )
        session.add(analysis)

    session.commit()