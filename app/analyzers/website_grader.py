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
                    "CRITICAL SCORING RULES:\n"
                    "1. Final total_score MUST reflect the actual quality of the site. Spread across the full 0-100 range.\n"
                    "2. Sites with NO SSL must score ≤35. Sites with SSL + mobile viewport start at ≥40.\n"
                    "3. Every item score MUST cite a specific piece of evidence from the raw data (CTA text, meta title, image counts, schema types, price counts, team names, etc.).\n"
                    "4. Missing pricing info → A3 and A4 score 0. No team info → B1 scores 0.\n"
                    "5. Thin content (<500 chars) → C1 and C2 cap at 1.\n"
                    "6. strengths array MUST have EXACTLY 3 entries. Each must name a concrete data point (e.g. 'SSL enabled', '3 CTAs detected: Call Now, Book, Get Quote', 'LocalBusiness schema present').\n"
                    "7. weaknesses array MUST have EXACTLY 3 entries. Each must name a concrete gap (e.g. 'No pricing shown – 0 price signals detected', 'Thin content: only 420 chars', 'No schema markup found').\n"
                    "8. recommendations array MUST have EXACTLY 3 entries. Each must be a specific, actionable fix tied to observed data (e.g. 'Add a visible price range on the homepage – currently 0 prices shown', 'Add LocalBusiness + Service schema – none detected', 'Add team bios/photos – 0 team members detected').\n"
                    "9. No two sites you grade in the same session should share the same total_score. The spread across all items must produce meaningfully different totals per site.\n"
                    "10. Forbidden: generic phrases like 'good website', 'needs improvement', 'consider adding'. Always tie feedback to specific counts, labels, or absence of data.\n"
                    "\n"
                    "Think like a customer: Would YOU hire this business based on their website alone?\n"
                    "Always reply with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,  # Moderate variety: wide enough to differentiate sites, low enough for consistent JSON structure
        "max_tokens": 1800,
        "top_p": 1.0,
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
If something cannot be verified, score it 0 and state the missing evidence explicitly.

SCORING RULES:
- 20 items, each scored 0/1/2 => total_points 0–40
- total_score (0–100) = round((total_points / 40) * 100)
- Score distribution guidelines:
    • Sites missing SSL OR mobile viewport: total_score must be ≤ 40
    • Sites with SSL + mobile viewport but missing CTAs + pricing: total_score 41–55
    • Sites with SSL + mobile + CTAs + pricing but no schema/team: total_score 56–70
    • Sites covering all major signals (SSL, mobile, CTAs, pricing, team, schema): total_score 71–90
    • Near-perfect sites with every signal present and strong content: total_score 91–100
- Each item's "evidence" field MUST quote or cite actual data from the RAW DATA section below
  (e.g. CTA labels, meta title text, image counts, schema type names, price counts, team names).
  Generic phrases like "present" or "needs improvement" without data citations are NOT acceptable.

OUTPUT:
- Return VALID JSON only, matching the required output shape.
- strengths: exactly 3 items, each citing a specific data signal (e.g. "SSL enabled", "3 CTAs: 'Call Now', 'Book', 'Get Quote'", "LocalBusiness schema detected").
- weaknesses: exactly 3 items, each citing a specific gap (e.g. "0 prices detected – pricing transparency unknown", "No team members found", "Missing mobile viewport meta tag").
- recommendations: exactly 3 items, each being a specific, actionable fix referencing observed data (e.g. "Add pricing to homepage – currently 0 price signals", "Implement LocalBusiness + Service schema – none detected", "Add team bios – 0 team members found").
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
A1. Primary CTA obvious above the fold: 2=CTA label present in data, 1=CTA exists but label generic, 0=no CTAs detected (0/1/2)
A2. Appointment/contact path frictionless: 2=phone+CTA present, 1=only one contact method, 0=neither (0/1/2)
A3. Front-end offer/pricing clearly stated: 2=prices detected, 1=services listed but no prices, 0=neither (0/1/2)
A4. Service pages optimized for conversion: 2=≥5 services listed with pricing, 1=services listed no pricing, 0=no services (0/1/2)
A5. Objection handling/FAQs present: 2=strong evidence in content, 1=weak signals, 0=not found (0/1/2)
A6. Message consistency (meta title ↔ H1 ↔ services): 2=title+H1+services aligned, 1=partial, 0=missing or mismatched (0/1/2)

Section B — Trust & Authority (max 10)
B1. Provider credibility visible: 2=team members named in data, 1=business name only, 0=no team info (0/1/2)
B2. Reviews/testimonials present: 2=testimonial signals in content, 1=rating mention only, 0=none (0/1/2)
B3. Results proof (before/after/outcomes): 2=explicit evidence, 1=implied, 0=none (0/1/2)
B4. Risk reducers/transparency (guarantees, policies): 2=clear signals, 1=implied, 0=none (0/1/2)
B5. Policies/compliance basics: 2=present in links, 1=implied, 0=not found (0/1/2)

Section C — Local SEO & Content Structure (max 10)
C1. Topical + location targeting: 2=local intent keywords detected, 1=location implied, 0=none (0/1/2)
C2. Dedicated service pages for core services: 2=≥3 services + links, 1=services listed, 0=none (0/1/2)
C3. Internal linking intentional: 2=≥10 links, 1=some links, 0=0-2 links (0/1/2)
C4. Schema markup relevant: 2=LocalBusiness/Service schema, 1=any schema, 0=none (0/1/2)
C5. NAP consistency + contact clarity: 2=phone+address in data, 1=one only, 0=neither (0/1/2)

Section D — Technical & UX Fundamentals (max 8)
D1. Mobile readiness: 2=mobile viewport present, 0=missing (0/2)
D2. SSL/HTTPS: 2=HTTPS, 0=HTTP only (0/2)
D3. Accessibility basics (alt text): 2=≥80% images have alt, 1=some alt text, 0=none (0/1/2)
D4. Content depth: 2=≥1000 chars, 1=500-999 chars, 0=<500 chars (0/1/2)

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
        {{"id":"A1","label":"Primary CTA obvious above the fold","score":0,"max":2,"evidence":"Cite exact CTA labels or 'No CTAs detected'"}}
      ]
    }},
    "trust_authority": {{ "score": 0, "max": 10, "items": [] }},
    "local_seo_structure": {{ "score": 0, "max": 10, "items": [] }},
    "technical_ux": {{ "score": 0, "max": 8, "items": [] }}
  }},
  "strengths": [
    "Specific strength 1 citing data signal",
    "Specific strength 2 citing data signal",
    "Specific strength 3 citing data signal"
  ],
  "weaknesses": [
    "Specific weakness 1 citing data gap",
    "Specific weakness 2 citing data gap",
    "Specific weakness 3 citing data gap"
  ],
  "recommendations": [
    "Specific fix 1 referencing observed data",
    "Specific fix 2 referencing observed data",
    "Specific fix 3 referencing observed data"
  ]
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