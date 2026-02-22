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
      service_quality_score, competitive_assessment, niche_specific_insights
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
                    "You are an expert business analyst specialising in revenue modelling. "
                    "Always reply with a valid JSON object and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
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
        return _parse_analysis(content)
    except requests.RequestException as exc:
        logger.error("Groq API request failed: %s", exc)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse Groq API response: %s", exc)

    return _empty_analysis()


def _build_prompt(data, niche):
    """Build the analysis prompt from scraped data."""
    services = ", ".join(data.get("services", [])) or "unknown"
    prices = ", ".join(data.get("prices", [])) or "unknown"
    team = ", ".join(data.get("team_members", []))[:200] or "unknown"

    ig = data.get("instagram") or {}
    ig_summary = (
        f"Instagram: @{ig.get('username')} | "
        f"{ig.get('followers', 0):,} followers | "
        f"{ig.get('engagement_rate', 0):.1f}% engagement"
        if ig.get("username")
        else "No Instagram found"
    )

    return f"""Analyse this {niche} business and return ONLY a JSON object with these exact keys:

Business: {data.get('name', 'Unknown')}
Location: {data.get('location', 'Unknown')}
Rating: {data.get('rating', 'N/A')} ({data.get('reviews_count', 0)} reviews)
Website: {data.get('website', 'None')}
Services: {services}
Prices: {prices}
Team: {team}
Social: {ig_summary}

Required JSON structure:
{{
  "revenue_streams": ["stream1", "stream2", "stream3"],
  "estimated_revenue_tier": "Low|Medium|High",
  "pricing_strategy": "Budget|Mid-tier|Premium|Luxury",
  "service_quality_score": 7.5,
  "competitive_assessment": "Brief 1-2 sentence assessment",
  "niche_specific_insights": "Brief 1-2 sentence niche insight"
}}"""


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
        "competitive_assessment": data.get("competitive_assessment", ""),
        "niche_specific_insights": data.get("niche_specific_insights", ""),
    }


def _empty_analysis():
    """Return an empty analysis skeleton when the API is unavailable."""
    return {
        "revenue_streams": [],
        "estimated_revenue_tier": None,
        "pricing_strategy": None,
        "service_quality_score": None,
        "competitive_assessment": None,
        "niche_specific_insights": None,
    }