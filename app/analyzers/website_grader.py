"""
Universal website grading system focused on Design & SEO.
Grades websites out of 100 points.
"""
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def grade_website(website_data):
    """
    Grade a website out of 100 based on Design (50pts) and SEO (50pts).
    
    Returns dict with:
      - total_score: 0-100
      - design_score: 0-50
      - seo_score: 0-50
      - strengths: list
      - weaknesses: list
      - recommendations: list
    """
    api_key = current_app.config.get("GROQ_API_KEY", "")
    
    if not api_key:
        logger.warning("GROQ_API_KEY is not set; skipping website grading.")
        return _empty_grade()
    
    # If no website data, return 0
    if not website_data or not website_data.get("url"):
        return _empty_grade()
    
    prompt = _build_grading_prompt(website_data)
    
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
                    "You are an expert web designer and SEO consultant. "
                    "Grade websites objectively based on design quality and SEO best practices. "
                    "Always reply with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Groq API error {response.status_code}: {response.text}")
            return _empty_grade()
        
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Website grade generated for {website_data.get('url', 'Unknown')}")
        return _parse_grade(content)
        
    except requests.RequestException as exc:
        logger.error("Groq API request failed for website grading: %s", exc)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse website grade response: %s", exc)
    
    return _empty_grade()


def _build_grading_prompt(data):
    """Build grading prompt from website data."""
    
    url = data.get("url", "Unknown")
    has_ssl = "https://" in url.lower()
    
    # Extract technical details
    meta_title = data.get("meta_title", "Missing")
    meta_desc = data.get("meta_description", "Missing")
    h1_tags = data.get("h1_tags", [])
    images_count = len(data.get("images", []))
    images_with_alt = len([img for img in data.get("images", []) if img.get("alt")])
    links_count = len(data.get("links", []))
    has_mobile_viewport = data.get("has_mobile_viewport", False)
    cta_buttons = data.get("cta_buttons", [])
    
    return f"""Grade this website out of 100 points based on Design (50 points) and SEO (50 points).

Website: {url}

TECHNICAL DATA:
- SSL Certificate: {"Yes" if has_ssl else "No"}
- Meta Title: {meta_title}
- Meta Description: {meta_desc}
- H1 Tags: {len(h1_tags)} found - {', '.join(h1_tags[:3])}
- Images: {images_count} total, {images_with_alt} with alt text ({int(images_with_alt/max(images_count,1)*100)}%)
- Internal Links: {links_count}
- Mobile Viewport Tag: {"Yes" if has_mobile_viewport else "No"}
- Call-to-Action Buttons: {len(cta_buttons)} found - {', '.join(cta_buttons[:3])}

CONTENT PREVIEW:
Services: {', '.join(data.get('services', [])[:5]) or 'None found'}
Text Length: {data.get('text_length', 0)} characters

GRADING RUBRIC:

DESIGN & UX (50 points):
- Visual appeal & professionalism (15 pts)
- Mobile responsiveness (10 pts) - check viewport tag, CTA visibility
- Page load optimization (10 pts) - image count, size indicators
- Clear navigation & structure (10 pts) - links, sections
- Call-to-action visibility (5 pts) - contact buttons, booking

SEO & DISCOVERABILITY (50 points):
- Meta tags quality (10 pts) - title and description present and descriptive
- Header structure (10 pts) - proper H1 usage
- Image optimization (10 pts) - alt text percentage
- SSL certificate (5 pts) - HTTPS
- Content quality (10 pts) - text length, keyword usage, service descriptions
- Internal linking (5 pts) - navigation structure

Return ONLY this JSON structure:
{{
  "total_score": 75,
  "design_score": 38,
  "seo_score": 37,
  "strengths": ["strength1", "strength2", "strength3"],
  "weaknesses": ["weakness1", "weakness2", "weakness3"],
  "recommendations": ["recommendation1", "recommendation2", "recommendation3"]
}}

Be objective and realistic. Most websites score 60-80. Only exceptional sites score 90+."""


def _parse_grade(content):
    """Parse and validate grade response from AI."""
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()
    
    data = json.loads(content)
    
    return {
        "total_score": int(data.get("total_score", 0)),
        "design_score": int(data.get("design_score", 0)),
        "seo_score": int(data.get("seo_score", 0)),
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "recommendations": data.get("recommendations", []),
    }


def _empty_grade():
    """Return empty grade when grading fails."""
    return {
        "total_score": 0,
        "design_score": 0,
        "seo_score": 0,
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
    }