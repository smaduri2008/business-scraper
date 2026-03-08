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
                    "Service quality scores should range from 3.0 to 9.5 based on actual indicators. "
                    "Provide detailed reasoning for your scores. "
                    "Always reply with a valid JSON object and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,  # INCREASED from 0.3 for more variety
        "max_tokens": 1500,  # INCREASED from 1024 for detailed reasoning
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
    
    # Handle team members
    team = ", ".join(data.get("team_members", [])[:10]) or "unknown"

    ig = data.get("instagram") or {}
    ig_summary = (
        f"Instagram: @{ig.get('username')} | "
        f"{ig.get('followers', 0):,} followers | "
        f"{ig.get('engagement_rate', 0):.1f}% engagement"
        if ig.get("username")
        else "No Instagram found"
    )

    return f"""Analyze this {niche} business SPECIFICALLY and INDIVIDUALLY. DO NOT give generic scores.

Business: {data.get('name', 'Unknown')}
Location: {data.get('location', 'Unknown')}
Rating: {data.get('rating', 'N/A')} ({data.get('reviews_count', 0)} reviews)
Website: {data.get('website', 'None')}
Services: {services}
Prices: {prices}
Team: {team}
Social: {ig_summary}

CRITICAL INSTRUCTIONS:
1. Service quality score should range from 3.0 to 9.5 based on actual indicators
2. Consider: rating ({data.get('rating')}), review count ({data.get('reviews_count')}), team size, services offered, pricing shown, social presence
3. Provide SPECIFIC reasoning referencing this business's data
4. DO NOT default to scores like 7.5 or 8.0 for every business
5. Low-quality indicators (low rating, no team, no prices) = 3.0-5.5
6. Average indicators (decent rating, some info) = 6.0-7.5
7. High-quality indicators (high rating, many reviews, full info) = 7.6-9.5

Required JSON structure:
{{
  "revenue_streams": ["specific stream 1", "specific stream 2", "specific stream 3"],
  "estimated_revenue_tier": "Low|Medium|High",
  "pricing_strategy": "Budget|Mid-tier|Premium|Luxury",
  "service_quality_score": 7.5,
  "service_quality_reasoning": "Detailed explanation: This business has a {data.get('rating')} rating with {data.get('reviews_count')} reviews. {'Team of ' + str(len(data.get('team_members', []))) + ' shown' if data.get('team_members') else 'No team information'}. {'Pricing shown' if prices != 'unknown' else 'No pricing transparency'}. Social presence: {ig_summary}. Based on these factors...",
  "competitive_assessment": "Specific 2-3 sentence assessment referencing this business's actual data",
  "niche_specific_insights": "Specific 2-3 sentence insight about THIS business in the {niche} niche"
}}

BE SPECIFIC. VARY YOUR SCORES. REFERENCE ACTUAL DATA."""


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
    rating = business_data.get("rating", 0)
    reviews = business_data.get("reviews_count", 0)
    
    if rating >= 4.5 and reviews >= 50:
        score += 20  # Successful business
    elif rating >= 4.0 and reviews >= 20:
        score += 15  # Decent business
    elif rating >= 3.5 and reviews >= 10:
        score += 5   # Okay business
    elif reviews < 5:
        score -= 15  # Too new or struggling
    
    # 3. Digital presence (some foundation = easier sell)
    ig_data = business_data.get("instagram", {})
    if ig_data and ig_data.get("followers", 0) > 1000:
        score += 10  # Has audience, understands digital
    elif ig_data and ig_data.get("followers", 0) > 500:
        score += 5
    
    # 4. Service business indicators (has team = has budget)
    team_count = len(business_data.get("team_members", []))
    services_count = len(business_data.get("services", []))
    
    if team_count >= 3:
        score += 10  # Multi-person business = bigger budget
    elif team_count >= 1:
        score += 5
    
    if services_count >= 5:
        score += 5  # Diverse services = more revenue
    
    # 5. Website exists but needs work (ideal scenario)
    has_website = bool(business_data.get("website"))
    if has_website and 30 < website_score < 60:
        score += 15  # PERFECT - has website but it's bad
    elif not has_website:
        score -= 10  # No website = need to build from scratch
    
    # Cap between 0-100
    return max(0, min(100, score))