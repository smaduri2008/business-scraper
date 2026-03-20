"""
Lead scoring and ranking for marketing outreach targeting.

A "lead" is a business that is a good prospect for web/marketing services:
  - Has a website that exists but scores poorly (ideal renovation target)
  - Is a legitimate, active business (decent rating + reviews)
  - Has at least one strong contact signal (phone / address / website)
  - NOT a business with an already-excellent website (nothing to sell them)  - NOT a brand-new or unestablished business (can't afford services)
"""

import logging

logger = logging.getLogger(__name__)

# ── Minimum thresholds to be considered a "qualified lead" ────────────────────
MIN_REVIEWS = 5          # Must have some social proof
MIN_RATING = 3.5         # Must not be a failing business

# ── Website score bands ───────────────────────────────────────────────────────
IDEAL_WEBSITE_MAX = 60   # Upper bound for "bad-but-existing website" sweet spot
EXCELLENT_WEBSITE = 75   # Threshold above which the website is good enough to deprioritize


def is_qualified_lead(business_data: dict) -> bool:
    """
    Return True when a business clears the minimum bar for outreach.

    Criteria:
    - At least one strong contact signal (phone, address, or website URL)
    - Minimum number of reviews
    - Minimum rating
    """
    has_contact = any([
        business_data.get("phone"),
        business_data.get("address"),
        business_data.get("website"),
    ])
    if not has_contact:
        return False

    reviews = business_data.get("reviews_count") or 0
    if reviews < MIN_REVIEWS:
        return False

    rating = business_data.get("rating") or 0
    if rating < MIN_RATING:
        return False

    return True


def compute_lead_score(business_data: dict) -> float:
    """
    Return the opportunity score for *business_data*.

    Tries, in order:
    1. analysis.opportunity_score (set by the AI analyser)
    2. Server-side calculation via _calculate_opportunity_score()

    Higher score → better outreach target.
    """
    analysis = business_data.get("analysis") or {}
    ai_score = analysis.get("opportunity_score")
    if ai_score is not None and ai_score > 0:
        return float(ai_score)

    # Fall back to the same deterministic formula used by ai_analyzer
    from app.analyzers.ai_analyzer import _calculate_opportunity_score  # noqa: PLC0415
    return float(_calculate_opportunity_score(
        business_data,
        business_data.get("website_grade") or {},
    ))


def rank_leads(businesses: list) -> list:
    """
    Sort *businesses* so the best outreach prospects come first.

    Strategy:
    - Qualified leads (meet minimum thresholds) are ranked before
      unqualified ones.
    - Within each group, businesses are ranked by opportunity score
      descending.
    - Businesses with an excellent website (≥ EXCELLENT_WEBSITE) are
      moved to the back of the qualified group because they are the
      lowest-value prospects for web/marketing renovation services.
    """
    def _score_and_bucket(b: dict):
        score = compute_lead_score(b)
        qualified = is_qualified_lead(b)

        wg = b.get("website_grade") or {}
        website_score = wg.get("total_score", 0)
        excellent_site = bool(b.get("website")) and website_score >= EXCELLENT_WEBSITE

        # Bucket priority (lower = sorted first):
        #  0 – qualified, non-excellent website  (best prospects)
        #  1 – qualified, excellent website       (deprioritized)
        #  2 – not qualified                      (worst prospects)
        if qualified and not excellent_site:
            bucket = 0
        elif qualified and excellent_site:
            bucket = 1
        else:
            bucket = 2

        # Deterministic tie-breakers within each bucket:
        # 1st: opportunity score (descending)
        # 2nd: reviews_count (descending) – more social proof = stronger business
        # 3rd: rating (descending) – higher quality = more budget
        # 4th: website_score (ascending) – worse site = more room to help
        try:
            reviews_tb = int(b.get("reviews_count") or 0)
        except (TypeError, ValueError):
            reviews_tb = 0

        try:
            rating_tb = float(b.get("rating") or 0.0)
        except (TypeError, ValueError):
            rating_tb = 0.0

        return (bucket, -score, -reviews_tb, -rating_tb, website_score)

    return sorted(businesses, key=_score_and_bucket)
