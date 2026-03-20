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
        "temperature": 0.25,  # HIGH temperature for maximum variety
        "max_tokens": 1500,
        "top_p": 1.0,  # Added for more diverse outputs
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
    """
    Website-only grading prompt using a 20-item rubric (0/1/2 each) => 0–40 points,
    scaled to 0–100 for total_score.
    """

    def _safe_str(x, default=""):
        return default if x is None else str(x)

    url = (_safe_str(data.get("url"), "Unknown") or "Unknown").strip()
    has_ssl = url.lower().startswith("https://")

    meta_title = _safe_str(data.get("meta_title"), "Missing")
    meta_desc = _safe_str(data.get("meta_description"), "Missing")

    h1_tags = data.get("h1_tags") or []
    links = data.get("links") or []
    images = data.get("images") or []
    cta_buttons = data.get("cta_buttons") or []
    services = data.get("services") or []
    prices = data.get("prices") or []
    team_members = data.get("team_members") or []
    text_length = int(data.get("text_length") or 0)
    has_mobile_viewport = bool(data.get("has_mobile_viewport") or False)

    images_count = len(images)
    images_with_alt = len([img for img in images if isinstance(img, dict) and img.get("alt")])
    alt_text_percentage = int(images_with_alt / max(images_count, 1) * 100) if images_count else 0

    # Optional fields (safe if not present)
    schema_types = data.get("schema_types") or []
    if isinstance(schema_types, str):
        schema_types = [schema_types]
    has_schema = bool(schema_types)

    # Heuristics / signals
    has_ctas = len(cta_buttons) > 0
    has_pricing = len(prices) > 0
    has_team = len(team_members) > 0
    has_adequate_content = text_length >= 500

    # If you have raw_text in website_data, it helps a lot. Otherwise keep it blank.
    raw_text = data.get("raw_text") if isinstance(data.get("raw_text"), str) else ""
    combined_text = " ".join([
        meta_title or "",
        meta_desc or "",
        " ".join([_safe_str(h) for h in h1_tags[:3]]),
        " ".join([_safe_str(s) for s in services[:10]]),
        raw_text[:1500],
    ]).lower()

    # This is a weak signal, but better than nothing without explicit city parsing.
    local_intent_keywords = ["near me", "located", "serving", "in "]
    has_local_intent = any(k in combined_text for k in local_intent_keywords)

    critical_issues = []
    if not has_ssl:
        critical_issues.append("❌ No SSL (HTTP only)")
    if not has_mobile_viewport:
        critical_issues.append("❌ Missing mobile viewport meta")
    if not has_ctas:
        critical_issues.append("⚠️ No CTA buttons detected")
    if text_length < 300:
        critical_issues.append("⚠️ Thin content (<300 chars)")

    positive_signals = []
    if has_ssl:
        positive_signals.append("✅ HTTPS enabled")
    if has_mobile_viewport:
        positive_signals.append("✅ Mobile viewport present")
    if has_ctas:
        positive_signals.append(f"✅ CTAs detected ({len(cta_buttons)})")
    if has_pricing:
        positive_signals.append(f"✅ Pricing cues detected ({len(prices)} items)")
    if has_team:
        positive_signals.append(f"✅ Team/provider cues detected ({len(team_members)} entries)")
    if has_schema:
        positive_signals.append(f"✅ Schema detected ({', '.join([_safe_str(t) for t in schema_types[:5]])})")

    return f"""
You are grading a local service business website using a WEBSITE-ONLY rubric.
You must ONLY score items you can verify from the raw data below.
If something cannot be verified from the data, score it conservatively (0 or 1) and say what evidence is missing.

SCORING:
- 20 items, each scored 0/1/2 => total_points 0–40
- total_score (0–100) = round((total_points / 40) * 100)

OUTPUT:
- Return VALID JSON only, matching the required output shape.
- Include item-level evidence tied to the raw data below (CTA text, meta title, counts, etc.).
- Do not mention ad accounts, tracking, bidding, or campaign setup (not website-gradable).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEBSITE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL: {url}

CRITICAL ISSUES (detected):
{chr(10).join(critical_issues) if critical_issues else "None detected"}

POSITIVE SIGNALS (detected):
{chr(10).join(positive_signals) if positive_signals else "None detected"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAW DATA (facts you must use)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECHNICAL:
- SSL (https): {"Yes" if has_ssl else "No"}
- Mobile viewport: {"Yes" if has_mobile_viewport else "No"}
- Meta title: "{meta_title}"
- Meta description: {"Present" if meta_desc != "Missing" and meta_desc.strip() else "Missing"}
- H1 tags count: {len(h1_tags)} (sample: {", ".join([f'"{_safe_str(h)}"' for h in h1_tags[:2]]) if h1_tags else "None"})
- Images: {images_count} (with alt: {images_with_alt}, {alt_text_percentage}%)
- Links count: {len(links)}

CONVERSION / CONTENT SIGNALS:
- CTA buttons ({len(cta_buttons)}): {", ".join([f'"{_safe_str(c)}"' for c in cta_buttons[:6]]) if cta_buttons else "None"}
- Services extracted ({len(services)}): {", ".join([f'"{_safe_str(s)}"' for s in services[:8]]) if services else "None"}
- Pricing extracted ({len(prices)}): {"Present" if has_pricing else "Not detected"}
- Team/provider extracted ({len(team_members)}): {"Present" if has_team else "Not detected"}
- Content length: {text_length} characters
- Schema types: {", ".join([_safe_str(t) for t in schema_types[:6]]) if schema_types else "None detected"}
- Local intent heuristic: {"Yes" if has_local_intent else "No/unclear"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUBRIC (website-only) — total 40 points
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Section A — Conversion & Offer Clarity (max 12)
A1. Primary CTA obvious above the fold (0–2)
A2. Appointment path frictionless (0–2)
A3. Front-end offer clearly stated (0–2)
A4. Service pages optimized for conversion intent (0–2)
A5. Objection handling present (0–2)
A6. Message consistency across site (0–2)

Section B — Trust & Authority (max 10)
B1. Provider credibility visible (0–2)
B2. Reviews/testimonials present and credible (0–2)
B3. Results proof (before/after/outcomes) where appropriate (0–2)
B4. Risk reducers/transparency (0–2)
B5. Policies/compliance basics (0–2)

Section C — Local SEO & Content Structure (max 10)
C1. Topical + location targeting exists (0–2)
C2. Dedicated service pages exist for core services (0–2)
C3. Internal linking between services is intentional (0–2)
C4. Schema markup present and relevant (0–2)
C5. NAP consistency + contact clarity (0–2)

Section D — Technical & UX Fundamentals (max 8)
D1. Mobile readiness (0–2)
D2. Page-speed hygiene (0–2)
D3. Accessibility basics (0–2)
D4. Contactability everywhere (0–2)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT JSON SHAPE (JSON ONLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "total_points": 0,
  "max_points": 40,
  "total_score": 0,
  "sections": {{
    "conversion_offer_clarity": {{
      "score": 0, "max": 12,
      "items": [
        {{"id":"A1","label":"Primary CTA obvious above the fold","score":0,"max":2,"evidence":"..."}}
      ]
    }},
    "trust_authority": {{ "score": 0, "max": 10, "items": [] }},
    "local_seo_structure": {{ "score": 0, "max": 10, "items": [] }},
    "technical_ux": {{ "score": 0, "max": 8, "items": [] }}
  }},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "recommendations": ["..."]
}}

Now grade the website strictly using only the raw data. Output JSON only.
""".strip()


def _parse_grade(content):
    """Parse and validate grade response from AI. Supports new rubric schema and old schema."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(line for line in lines if not line.startswith("```")).strip()

    data = json.loads(content)

    # New rubric schema
    if "sections" in data and "total_points" in data:
        total_points = int(data.get("total_points") or 0)
        max_points = int(data.get("max_points") or 40)
        total_score = data.get("total_score")

        if total_score is None and max_points > 0:
            total_score = round((total_points / max_points) * 100)

        return {
            "total_score": int(max(0, min(100, int(total_score or 0)))),
            # Keep legacy keys for existing UI/backcompat
            "website_quality_score": 0,
            "digital_presence_score": 0,
            "strengths": data.get("strengths", []) or [],
            "weaknesses": data.get("weaknesses", []) or [],
            "recommendations": data.get("recommendations", []) or [],
            "detailed_breakdown": {
                "rubric_v2": {
                    "total_points": total_points,
                    "max_points": max_points,
                    "sections": data.get("sections") or {},
                }
            },
        }

    # Old schema fallback
    detailed_breakdown = {}
    raw_breakdown = data.get("detailed_breakdown", {}) or {}
    for key, value in raw_breakdown.items():
        if isinstance(value, dict):
            detailed_breakdown[key] = value
        else:
            detailed_breakdown[key] = {"score": int(value), "reasoning": ""}

    return {
        "total_score": int(data.get("total_score", 0) or 0),
        "website_quality_score": int(data.get("website_quality_score", 0) or 0),
        "digital_presence_score": int(data.get("digital_presence_score", 0) or 0),
        "strengths": data.get("strengths", []) or [],
        "weaknesses": data.get("weaknesses", []) or [],
        "recommendations": data.get("recommendations", []) or [],
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
        "detailed_breakdown": {
            "rubric_v2": {
                "total_points": 0,
                "max_points": 40,
                "sections": {},
            }
        },
    }