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
                    "You are a brutally honest website conversion expert who grades local service business websites. "
                    "You have personally audited over 10,000 websites and know exactly what converts and what doesn't. "
                    "\n\n"
                    "CRITICAL RULES:\n"
                    "1. Scores MUST range from 25-92. Never give a score between 55-65 unless truly average.\n"
                    "2. Most websites are either bad (30-50) or decent (70-85). Very few are perfect (85+).\n"
                    "3. Missing prices = automatic -15 points from conversion score.\n"
                    "4. No team photos = automatic -10 points from trust score.\n"
                    "5. No social proof/testimonials = automatic -12 points.\n"
                    "6. HTTP only (no SSL) = automatic score below 35 maximum.\n"
                    "7. Missing mobile viewport = automatic score below 40 maximum.\n"
                    "8. Every website is DIFFERENT. No two sites should score within 3 points of each other.\n"
                    "9. Be SPECIFIC about what's good and bad. Generic feedback is worthless.\n"
                    "10. Your reasoning should reference actual data from the website, not assumptions.\n"
                    "\n"
                    "Think like a customer: Would YOU hire this business based on their website alone?\n"
                    "Always reply with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,  # HIGH temperature for maximum variety
        "max_tokens": 2500,
        "top_p": 0.95,  # Added for more diverse outputs
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
    text_length = data.get("text_length", 0)
    
    # Calculate some quality indicators
    alt_text_percentage = int(images_with_alt/max(images_count,1)*100) if images_count > 0 else 0
    has_adequate_content = text_length >= 500
    has_pricing = len(prices) > 0
    has_team = len(team_members) > 0
    has_services = len(services) >= 3
    
    # Build critical assessment
    critical_issues = []
    if not has_ssl:
        critical_issues.append("❌ NO SSL CERTIFICATE - Major trust and security issue")
    if not has_mobile_viewport:
        critical_issues.append("❌ NOT MOBILE RESPONSIVE - Loses 60% of potential customers")
    if not has_pricing:
        critical_issues.append("⚠️ NO PRICING - Major conversion barrier")
    if not has_team:
        critical_issues.append("⚠️ NO TEAM PHOTOS - Missing trust signals")
    if len(cta_buttons) == 0:
        critical_issues.append("❌ NO CLEAR CALL-TO-ACTION - How do customers book?")
    if not has_services:
        critical_issues.append("⚠️ SERVICES UNCLEAR - Fewer than 3 services identified")
    if text_length < 300:
        critical_issues.append("⚠️ THIN CONTENT - Looks unprofessional and hurts SEO")
    
    positive_signals = []
    if has_ssl:
        positive_signals.append("✅ SSL Certificate")
    if has_mobile_viewport:
        positive_signals.append("✅ Mobile Responsive")
    if has_pricing:
        positive_signals.append(f"✅ Pricing Shown ({len(prices)} items)")
    if has_team:
        positive_signals.append(f"✅ Team Displayed ({len(team_members)} members)")
    if len(cta_buttons) >= 3:
        positive_signals.append(f"✅ Multiple CTAs ({len(cta_buttons)} found)")
    if has_adequate_content:
        positive_signals.append(f"✅ Good Content Volume ({text_length} chars)")
    if alt_text_percentage >= 70:
        positive_signals.append(f"✅ Good Image Optimization ({alt_text_percentage}% with alt text)")
    
    return f"""You are auditing this local service business website. Grade it out of 100 points.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEBSITE: {url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 CRITICAL ISSUES DETECTED:
{chr(10).join(critical_issues) if critical_issues else "None - Good baseline!"}

✅ POSITIVE SIGNALS:
{chr(10).join(positive_signals) if positive_signals else "Very few positive signals detected"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAW DATA FOR YOUR ANALYSIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TECHNICAL:
• SSL: {"✅ Yes" if has_ssl else "❌ NO"}
• Mobile Viewport: {"✅ Yes" if has_mobile_viewport else "❌ NO"}
• Meta Title: "{meta_title}"
• Meta Description: {"✅ Present" if meta_desc != "Missing" else "❌ Missing"}
• H1 Tags: {len(h1_tags)} found → {', '.join([f'"{h1}"' for h1 in h1_tags[:2]]) if h1_tags else 'None'}
• Images: {images_count} total, {images_with_alt} with alt text ({alt_text_percentage}%)
• Internal Links: {links_count}

CONVERSION ELEMENTS:
• CTAs: {len(cta_buttons)} buttons → {', '.join([f'"{cta}"' for cta in cta_buttons[:4]]) if cta_buttons else 'None found'}
• Services Listed: {len(services)} → {', '.join([f'"{s}"' for s in services[:5]]) if services else 'None clearly identified'}
• Pricing: {"✅ " + str(len(prices)) + " prices shown" if has_pricing else "❌ No prices displayed"}
• Team: {"✅ " + str(len(team_members)) + " members shown" if has_team else "❌ No team information"}
• Content Volume: {text_length} characters {"✅ (adequate)" if has_adequate_content else "❌ (too thin)"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SCORING FRAMEWORK (100 points):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PART 1: WEBSITE QUALITY (50 points max)

1. Conversion Optimization (15 pts)
   • Clear value proposition visible immediately: 0-3 pts
   • Multiple clear CTAs (book, call, contact): 0-3 pts
   • Contact info prominent and easy to find: 0-3 pts
   • Pricing transparency or "free consultation": 0-3 pts
   • Social proof (testimonials, reviews, before/after): 0-3 pts
   
   PENALTY: -15 pts if no pricing AND no "free consultation" offer
   PENALTY: -10 pts if no CTAs above the fold

2. User Experience (15 pts)
   • Mobile responsive design: 0-5 pts
   • Fast loading indicators (reasonable images): 0-4 pts
   • Clean, professional aesthetics: 0-3 pts
   • Easy navigation structure: 0-3 pts
   
   PENALTY: -15 pts if not mobile responsive
   PENALTY: -5 pts if more than 50 images (slow loading)

3. Content Quality (10 pts)
   • Services clearly and specifically described: 0-3 pts
   • Adequate text content (500+ chars): 0-2 pts
   • Team/provider info builds trust: 0-3 pts
   • Educational or helpful content: 0-2 pts
   
   PENALTY: -8 pts if less than 300 characters of content

4. Technical SEO (10 pts)
   • HTTPS/SSL enabled: 0-3 pts (CRITICAL)
   • Meta title descriptive: 0-2 pts
   • Meta description present: 0-2 pts
   • Proper H1 usage (1-2 H1s): 0-2 pts
   • Image alt text (50%+ coverage): 0-1 pt
   
   PENALTY: Maximum score of 35 total if no SSL

PART 2: DIGITAL PRESENCE (50 points max)

5. Local SEO (12 pts)
   • Location in meta title: 0-4 pts
   • Service + location keywords in content: 0-4 pts
   • Local area targeting evident: 0-4 pts

6. Trust & Credibility (15 pts)
   • Team photos/provider visible: 0-5 pts
   • Credentials or certifications: 0-5 pts
   • Real business address/location: 0-3 pts
   • Trust badges or associations: 0-2 pts
   
   PENALTY: -10 pts if no team shown

7. Lead Generation (13 pts)
   • Multiple contact methods: 0-4 pts
   • Booking/scheduling system: 0-5 pts
   • Lead magnets or free offers: 0-4 pts

8. Engagement (10 pts)
   • Social media links: 0-2 pts
   • Email signup option: 0-2 pts
   • Blog or resources section: 0-3 pts
   • Portfolio or before/after gallery: 0-3 pts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRADING INSTRUCTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Start with the raw data above
2. Apply the scoring framework strictly
3. Apply ALL relevant penalties
4. Be brutally honest - most websites are mediocre (45-65 range)
5. Only give 75+ to websites that are genuinely well-optimized
6. Give under 40 to websites with critical issues (no SSL, not mobile, no CTAs)
7. Your reasoning MUST cite specific data points from above
8. Make each grade unique - no two websites should score the same

REQUIRED OUTPUT FORMAT (JSON only):

{{
  "total_score": 47,
  "website_quality_score": 22,
  "digital_presence_score": 25,
  "strengths": [
    "Specific strength #1 with data reference",
    "Specific strength #2 with numbers",
    "Specific strength #3"
  ],
  "weaknesses": [
    "Critical weakness #1 - explain impact",
    "Major weakness #2 - be specific",
    "Weakness #3 with recommendation"
  ],
  "recommendations": [
    "Actionable fix #1 with specific instruction",
    "Priority fix #2 with expected impact",
    "Quick win #3"
  ],
  "detailed_breakdown": {{
    "conversion_optimization": {{
      "score": 6,
      "reasoning": "Found {len(cta_buttons)} CTAs but NO PRICING displayed (-15 pt penalty). {len(services)} services listed but descriptions are vague. No social proof visible."
    }},
    "user_experience": {{
      "score": 8,
      "reasoning": "Mobile viewport present (+5) but {images_count} images may slow loading. Navigation appears {'clear' if links_count > 10 else 'limited'}."
    }},
    "content_quality": {{
      "score": 4,
      "reasoning": "Only {text_length} characters of content - WAY too thin (-8 pts). {'Team shown is good (+3)' if has_team else 'No team info hurts trust'}. Services: {len(services)}."
    }},
    "technical_seo": {{
      "score": 4,
      "reasoning": "{'SSL enabled (+3)' if has_ssl else 'NO SSL - CRITICAL ISSUE (max score 35)'}. Meta: '{meta_title[:40]}...' Images: {alt_text_percentage}% have alt text."
    }},
    "local_seo": {{
      "score": 7,
      "reasoning": "Analyze if '{url}' and services target local area. Check if city/neighborhood appears in content."
    }},
    "trust_credibility": {{
      "score": 5,
      "reasoning": "{'Shows ' + str(len(team_members)) + ' team members (+5)' if has_team else 'NO team photos visible - major trust issue (-10)'}.  Check for certifications."
    }},
    "lead_generation": {{
      "score": 6,
      "reasoning": "{len(cta_buttons)} CTAs found. Evaluate if booking system present, if lead magnets offered, if multiple contact methods exist."
    }},
    "engagement": {{
      "score": 5,
      "reasoning": "Assess social links, email signup, blog presence, portfolio. Most service sites lack engagement features."
    }}
  }}
}}

Grade this website NOW. Be harsh but fair. Reference the actual data above."""


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