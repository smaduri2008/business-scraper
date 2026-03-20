"""
AI-powered revenue and business analysis using the Groq API (free tier).
"""
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def analyze_business(business_data, niche):
    """
    Send scraped business data to Groq and return a structured analysis dict.

    Returns a dict with:
      revenue_streams, estimated_revenue_tier, pricing_strategy,
      service_quality_score, competitive_assessment, niche_specific_insights,
      opportunity_score
    """
    api_key = current_app.config.get("GROQ_API_KEY", "")
    
    if not api_key:
        logger.warning("GROQ_API_KEY is not set; skipping AI analysis.")
        return _empty_analysis()

    prompt = _build_prompt(business_data, niche)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert business analyst specializing in local service businesses. "
                    "Analyze each business individually and provide varied, specific assessments. "
                    "\n\n"
                    "SERVICE QUALITY SCORE BANDS (3.0–9.5 — use the full range):\n"
                    "  3.0–4.4 → Poor: rating <3.5 OR fewer than 5 reviews AND no pricing AND no team info\n"
                    "  4.5–5.9 → Below average: rating 3.5–3.9, few reviews, sparse info\n"
                    "  6.0–7.0 → Average: rating 4.0–4.2, 10–49 reviews, some info shown\n"
                    "  7.1–8.0 → Good: rating 4.3–4.6, 50–199 reviews, pricing or team visible\n"
                    "  8.1–9.0 → Very good: rating 4.7–4.8, 200+ reviews, pricing AND team visible\n"
                    "  9.1–9.5 → Excellent: rating 4.9–5.0, 500+ reviews, full info + strong social\n"
                    "\n"
                    "SCORING RULES:\n"
                    "1. Assign service_quality_score strictly from the band that matches the business's actual data.\n"
                    "2. NEVER default to 7.5 or 8.0. Pick the score that honestly reflects the evidence.\n"
                    "3. service_quality_reasoning MUST cite the specific rating, review count, pricing status, team size, and social presence.\n"
                    "4. competitive_assessment MUST name at least one specific competitive advantage or disadvantage visible in the data.\n"
                    "5. niche_specific_insights MUST name the niche and reference a concrete revenue or market signal.\n"
                    "6. revenue_streams MUST list 3 specific streams plausible for this business's services and pricing.\n"
                    "7. pricing_strategy MUST be one of: Budget / Mid-tier / Premium / Luxury — justified by actual price signals.\n"
                    "Always reply with a valid JSON object and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 1500,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        # Add detailed error logging
        if response.status_code != 200:
            logger.error(f"Groq API error {response.status_code}: {response.text}")
            return _empty_analysis()
        
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Groq API response received for {business_data.get('name', 'Unknown')}")
        
        # Parse the analysis result
        result = _parse_analysis(content)
        
        # Calculate and add opportunity score
        opportunity_score = _calculate_opportunity_score(
            business_data, 
            business_data.get("website_grade", {})
        )
        result["opportunity_score"] = opportunity_score
        
        return result
        
    except requests.RequestException as exc:
        logger.error("Groq API request failed: %s", exc)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse Groq API response: %s", exc)

    return _empty_analysis()


def _build_prompt(data, niche):
    """Build the analysis prompt from scraped data."""
    
    # Handle services
    services = ", ".join(data.get("services", [])[:10]) or "unknown"
    
    # Handle prices - support both dict and string format
    price_list = data.get("prices", [])
    if price_list and isinstance(price_list[0], dict):
        prices = ", ".join([p.get("price", "") for p in price_list[:10]]) or "unknown"
    elif price_list:
        prices = ", ".join([str(p) for p in price_list[:10]]) or "unknown"
    else:
        prices = "unknown"

    has_pricing = prices != "unknown"
    
    # Handle team members
    team_members = data.get("team_members", [])
    team = ", ".join(team_members[:10]) or "unknown"
    team_count = len(team_members)

    ig = data.get("instagram") or {}
    ig_followers = ig.get("followers", 0) or 0
    ig_engagement = ig.get("engagement_rate", 0) or 0
    ig_summary = (
        f"Instagram: @{ig.get('username')} | "
        f"{ig_followers:,} followers | "
        f"{ig_engagement:.1f}% engagement"
        if ig.get("username")
        else "No Instagram found"
    )

    rating = data.get("rating", "N/A")
    reviews_count = data.get("reviews_count", 0) or 0

    # Derive band hint for the model
    try:
        r = float(rating)
    except (TypeError, ValueError):
        r = 0.0
    if r < 3.5 or reviews_count < 5:
        band_hint = "3.0–4.4 (Poor)"
    elif r < 4.0:
        band_hint = "4.5–5.9 (Below average)"
    elif r < 4.3:
        band_hint = "6.0–7.0 (Average)"
    elif r < 4.7:
        band_hint = "7.1–8.0 (Good)"
    elif r < 4.9:
        band_hint = "8.1–9.0 (Very good)"
    else:
        band_hint = "9.1–9.5 (Excellent)"

    return f"""Analyze this {niche} business SPECIFICALLY and INDIVIDUALLY. DO NOT give generic scores.

Business: {data.get('name', 'Unknown')}
Location: {data.get('location', 'Unknown')}
Rating: {rating} ({reviews_count} reviews)
Website: {data.get('website', 'None')}
Services ({len(data.get('services', []))}): {services}
Pricing transparency: {"YES – prices detected: " + prices if has_pricing else "NO – no pricing shown"}
Team ({team_count} members): {team}
Social: {ig_summary}

SCORE BAND for this business: {band_hint}
(Justify any deviation from this band in service_quality_reasoning)

Required JSON structure:
{{
  "revenue_streams": ["specific stream 1 for {niche}", "specific stream 2 for {niche}", "specific stream 3 for {niche}"],
  "estimated_revenue_tier": "Low|Medium|High",
  "pricing_strategy": "Budget|Mid-tier|Premium|Luxury",
  "service_quality_score": 0.0,
  "service_quality_reasoning": "This {niche} business has a {rating} rating with {reviews_count} reviews. Team: {team_count} members {'(' + team + ')' if team != 'unknown' else '(none shown)'}. Pricing: {'shown (' + prices + ')' if has_pricing else 'not shown'}. Social: {ig_summary}. Based on these indicators, the score falls in the {band_hint} band because...",
  "competitive_assessment": "2-3 sentences naming at least one specific competitive advantage or disadvantage visible in this business's actual data",
  "niche_specific_insights": "2-3 sentences about THIS {niche} business referencing a concrete revenue or market signal from the data above"
}}

BE SPECIFIC. USE THE BAND. REFERENCE ACTUAL DATA."""


def _parse_analysis(content):
    """Extract and validate a JSON analysis from the model response."""
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    data = json.loads(content)

    return {
        "revenue_streams": data.get("revenue_streams", []),
        "estimated_revenue_tier": data.get("estimated_revenue_tier", "Unknown"),
        "pricing_strategy": data.get("pricing_strategy", "Unknown"),
        "service_quality_score": float(data.get("service_quality_score", 0)),
        "service_quality_reasoning": data.get("service_quality_reasoning", ""),
        "competitive_assessment": data.get("competitive_assessment", ""),
        "niche_specific_insights": data.get("niche_specific_insights", ""),
        "opportunity_score": data.get("opportunity_score", 0),
    }


def _empty_analysis():
    """Return an empty analysis skeleton when the API is unavailable."""
    return {
        "revenue_streams": [],
        "estimated_revenue_tier": None,
        "pricing_strategy": None,
        "service_quality_score": None,
        "service_quality_reasoning": None,
        "competitive_assessment": None,
        "niche_specific_insights": None,
        "opportunity_score": 0,
    }


def _calculate_opportunity_score(business_data, website_grade):
    """
    Calculate how good of an opportunity this business is for marketing services.
    Higher score = better target (bad website but successful business).
    
    Perfect target: Busy business (good reviews) with terrible website.
    Bad target: Great website (nothing to improve) or failing business (can't afford you).
    """
    score = 50  # Start at neutral
    
    # 1. Website quality (inverted - worse website = better opportunity)
    website_score = website_grade.get("total_score", 50)
    if website_score == 0:
        score -= 30  # No website at all = too much work
    elif website_score < 40:
        score += 25  # Terrible website = great opportunity
    elif website_score < 55:
        score += 20  # Bad website = good opportunity
    elif website_score < 70:
        score += 10  # Mediocre website = decent opportunity
    elif website_score < 85:
        score += 0   # Good website = neutral
    else:
        score -= 20  # Excellent website = nothing to improve
    
    # 2. Business health (good business = can afford you)
    rating_raw = business_data.get("rating")
    reviews_raw = business_data.get("reviews_count")

    # Coerce None/empty to numbers
    try:
        rating = float(rating_raw) if rating_raw is not None else 0.0
    except (TypeError, ValueError):
        rating = 0.0

    try:
        reviews = int(reviews_raw) if reviews_raw is not None else 0
    except (TypeError, ValueError):
        reviews = 0

    if rating >= 4.5 and reviews >= 50:
        score += 20
    elif rating >= 4.0 and reviews >= 20:
        score += 15
    elif rating >= 3.5 and reviews >= 10:
        score += 5
    elif reviews < 5:
        score -= 15
    
    # 3. Digital presence – social followers signal brand awareness
    ig_data = business_data.get("instagram") or {}
    ig_followers = ig_data.get("followers", 0) or 0
    ig_engagement = ig_data.get("engagement_rate", 0) or 0
    if ig_followers > 5000:
        score += 12  # Large audience already → strong digital intent
    elif ig_followers > 1000:
        score += 8
    elif ig_followers > 500:
        score += 4

    # Engagement rate bonus (active audience is a valuable upsell signal)
    if ig_engagement >= 4.0:
        score += 6   # High engagement → audience responsive to content
    elif ig_engagement >= 2.0:
        score += 3

    # 4. Price transparency (no pricing = clear improvement we can sell)
    price_list = business_data.get("prices", [])
    has_pricing = bool(price_list)
    if not has_pricing:
        score += 8   # No pricing shown = explicit gap we can improve
    
    # 5. Service business indicators (has team = has budget)
    team_count = len(business_data.get("team_members", []))
    services_count = len(business_data.get("services", []))
    
    if team_count >= 3:
        score += 10  # Multi-person business = bigger budget
    elif team_count >= 1:
        score += 5
    
    if services_count >= 5:
        score += 5  # Diverse services = more revenue
    
    # 6. Website exists but needs work (ideal scenario)
    has_website = bool(business_data.get("website"))
    if has_website and 30 < website_score < 60:
        score += 15  # PERFECT - has website but it's bad
    elif not has_website:
        score -= 10  # No website = need to build from scratch
    
    # Cap between 0-100
    return max(0, min(100, score))