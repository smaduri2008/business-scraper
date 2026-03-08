"""
Universal website grading system for local service businesses.
Grades websites out of 100 points based on graded criteria.
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
    Grade a website out of 100 based on Website Quality (50pts) and Digital Presence (50pts).
    
    Returns dict with:
      - total_score: 0-100
      - website_quality_score: 0-50
      - digital_presence_score: 0-50
      - strengths: list
      - weaknesses: list
      - recommendations: list
      - detailed_breakdown: dict with individual category scores AND reasoning
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
                    "You are an expert digital marketing consultant specializing in local service businesses. "
                    "Grade websites based on conversion optimization, user experience, and digital marketing best practices. "
                    "Be critical and vary your scores based on actual differences between websites. "
                    "Provide detailed reasoning for each score. "
                    "Scores should range from 20-95 based on quality. Don't cluster around 60. "
                    "Always reply with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,  # INCREASED from 0.2 for more variety
        "max_tokens": 2000,  # INCREASED from 1200 for detailed reasoning
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
    services = data.get("services", [])
    prices = data.get("prices", [])
    team_members = data.get("team_members", [])
    
    return f"""Grade this local service business website out of 100 points. BE CRITICAL and DETAILED.

Website: {url}

TECHNICAL DATA:
- SSL Certificate: {"Yes" if has_ssl else "No"}
- Meta Title: {meta_title}
- Meta Description: {meta_desc}
- H1 Tags: {len(h1_tags)} found - {', '.join(h1_tags[:3]) if h1_tags else 'None'}
- Images: {images_count} total, {images_with_alt} with alt text ({int(images_with_alt/max(images_count,1)*100)}%)
- Internal Links: {links_count}
- Mobile Viewport Tag: {"Yes" if has_mobile_viewport else "No"}
- Call-to-Action Buttons: {len(cta_buttons)} found - {', '.join(cta_buttons[:3]) if cta_buttons else 'None'}

BUSINESS DATA:
- Services Listed: {len(services)} - {', '.join(services[:5]) if services else 'None found'}
- Prices Displayed: {"Yes" if prices else "No"} ({len(prices)} items)
- Team Members Shown: {"Yes" if team_members else "No"} ({len(team_members)} members)
- Text Content Length: {data.get('text_length', 0)} characters

GRADING RUBRIC (100 points total):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEBSITE QUALITY (50 points)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CONVERSION OPTIMIZATION (15 points)
   - Clear primary offer or front-end offer visible (3 pts)
   - Multiple clear CTAs (book now, contact, call) (3 pts)
   - Contact information easily accessible (phone, form) (3 pts)
   - Pricing transparency (prices shown or "free consultation") (3 pts)
   - Social proof visible (reviews, testimonials, before/after) (3 pts)

2. USER EXPERIENCE & DESIGN (15 points)
   - Professional, modern design (5 pts)
   - Mobile responsive (viewport tag present) (5 pts)
   - Fast-loading indicators (reasonable image count) (3 pts)
   - Clear navigation structure (2 pts)

3. CONTENT QUALITY (10 points)
   - Services clearly described (3 pts)
   - Adequate text content (500+ characters) (2 pts)
   - Team/provider information shown (builds trust) (3 pts)
   - Educational or helpful content present (2 pts)

4. TECHNICAL SEO BASICS (10 points)
   - HTTPS/SSL enabled (2 pts)
   - Meta title present and descriptive (2 pts)
   - Meta description present (2 pts)
   - Proper H1 tag usage (1-2 H1s) (2 pts)
   - Image alt text present (50%+ images) (2 pts)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIGITAL PRESENCE & FINDABILITY (50 points)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. LOCAL SEO INDICATORS (15 points)
   - Location mentioned in meta title (5 pts)
   - Service + location keywords in content (5 pts)
   - Local area targeting evident (neighborhood, city mentioned) (5 pts)

6. TRUST & CREDIBILITY (15 points)
   - Team photos or provider visible (5 pts)
   - Professional credentials or certifications mentioned (5 pts)
   - Real business address or location indicators (3 pts)
   - Trust badges, associations, or partnerships (2 pts)

7. LEAD GENERATION SETUP (10 points)
   - Multiple contact methods offered (3 pts)
   - Booking/scheduling system present or linked (4 pts)
   - Lead magnets or free consultation offers (3 pts)

8. ENGAGEMENT & RETENTION (10 points)
   - Social media links present (2 pts)
   - Email signup or newsletter option (2 pts)
   - Blog or educational content section (3 pts)
   - Before/after gallery or portfolio (3 pts)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT INSTRUCTIONS:
1. Vary your scores significantly based on actual quality differences
2. Provide SPECIFIC reasoning for each category score
3. Don't default to middle scores (avoid clustering around 60-70)
4. Be harsh on sites with real problems (score 30-50)
5. Be generous with well-optimized sites (score 80-95)
6. Reference specific elements from the data in your reasoning

Return ONLY this JSON structure:
{{
  "total_score": 72,
  "website_quality_score": 38,
  "digital_presence_score": 34,
  "strengths": ["Clear CTAs with multiple booking options", "Strong service descriptions", "Good use of social proof"],
  "weaknesses": ["No pricing transparency", "Missing team member information", "Weak local SEO signals"],
  "recommendations": ["Add transparent pricing or starting prices", "Include team bios with photos", "Optimize meta title with location"],
  "detailed_breakdown": {{
    "conversion_optimization": {{
      "score": 12,
      "reasoning": "Has {len(cta_buttons)} CTAs which is good, but pricing is not shown reducing transparency. Social proof is missing."
    }},
    "user_experience": {{
      "score": 13,
      "reasoning": "Mobile viewport tag present, {images_count} images suggests reasonable load time. Navigation appears clear."
    }},
    "content_quality": {{
      "score": 7,
      "reasoning": "{len(services)} services listed is excellent, but only {data.get('text_length', 0)} characters of content. {'Team shown' if team_members else 'No team information'}."
    }},
    "technical_seo": {{
      "score": 6,
      "reasoning": "{'SSL enabled' if has_ssl else 'NO SSL - major issue'}. Meta title: {meta_title[:50]}... {'Present' if meta_desc else 'MISSING meta description'}. {len(h1_tags)} H1 tags found."
    }},
    "local_seo": {{
      "score": 10,
      "reasoning": "Analyze if location appears in title, services mention location, local area targeting."
    }},
    "trust_credibility": {{
      "score": 9,
      "reasoning": "{'Team of ' + str(len(team_members)) + ' shown' if team_members else 'NO team shown'}. Look for credentials, address, trust badges."
    }},
    "lead_generation": {{
      "score": 7,
      "reasoning": "{len(cta_buttons)} CTAs found. Check for booking system, lead magnets, multiple contact methods."
    }},
    "engagement": {{
      "score": 8,
      "reasoning": "Look for social links, email signup, blog, portfolio. Evaluate engagement potential."
    }}
  }}
}}

DO NOT give similar scores to different websites. Each site should have a unique score based on its actual quality."""

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
    
    # Parse detailed breakdown with reasoning
    detailed_breakdown = {}
    raw_breakdown = data.get("detailed_breakdown", {})
    
    for key, value in raw_breakdown.items():
        if isinstance(value, dict):
            detailed_breakdown[key] = value
        else:
            # Backwards compatible - if just a number
            detailed_breakdown[key] = {
                "score": int(value),
                "reasoning": ""
            }
    
    return {
        "total_score": int(data.get("total_score", 0)),
        "website_quality_score": int(data.get("website_quality_score", 0)),
        "digital_presence_score": int(data.get("digital_presence_score", 0)),
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "recommendations": data.get("recommendations", []),
        "detailed_breakdown": detailed_breakdown,
    }


def _empty_grade():
    """Return empty grade when grading fails."""
    return {
        "total_score": 0,
        "website_quality_score": 0,
        "digital_presence_score": 0,
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "detailed_breakdown": {},
    }