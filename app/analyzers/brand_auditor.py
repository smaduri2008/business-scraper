"""
AI-powered brand audit using the Groq API.

Generates concise brand summaries, positioning guesses, conversion notes,
and prioritised recommendations from scraped website data.
"""
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def generate_brand_audit(website_data: dict, brand_info: dict) -> dict:
    """
    Send website data + extracted brand info to Groq and return a structured
    audit dict.

    Returns:
        {
          "brand_summary": [...],         # 3-6 bullets
          "positioning_guess": "...",     # 1-2 sentences
          "conversion_notes": [...],      # 3-6 bullets tied to evidence
          "top_recommendations": [...]    # 3-6 prioritised actions with "because…"
        }
    """
    api_key = current_app.config.get("GROQ_API_KEY", "")
    if not api_key:
        logger.warning("GROQ_API_KEY not set; skipping brand audit.")
        return _empty_audit()

    prompt = _build_prompt(website_data, brand_info)

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
                    "You are an elite brand strategist and conversion rate optimiser. "
                    "You analyse websites and produce concise, evidence-based brand audits. "
                    "Your bullets are specific – they always reference actual data from the "
                    "website (CTAs found, pricing shown, team listed, images count, etc.). "
                    "Never produce generic advice. "
                    "Reply with valid JSON only – no markdown, no extra text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
        "top_p": 0.9,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            logger.error("Groq API error %s: %s", response.status_code, response.text)
            return _empty_audit()
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_audit(content)

    except requests.RequestException as exc:
        logger.error("Groq API request failed for brand audit: %s", exc)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse brand audit response: %s", exc)

    return _empty_audit()


def _build_prompt(website_data: dict, brand_info: dict) -> str:
    url = website_data.get("url", "Unknown")
    brand_name = brand_info.get("name") or "Unknown"
    phones = brand_info.get("phones", [])
    emails = brand_info.get("emails", [])
    addresses = brand_info.get("addresses", [])
    socials = brand_info.get("socials", {})

    services = website_data.get("services", [])
    prices = website_data.get("prices", [])
    team = website_data.get("team_members", [])
    ctas = website_data.get("cta_buttons", [])
    h1s = website_data.get("h1_tags", [])
    meta_title = website_data.get("meta_title", "")
    meta_desc = website_data.get("meta_description", "")
    text_length = website_data.get("text_length", 0)
    has_mobile = website_data.get("has_mobile_viewport", False)
    images = website_data.get("images", [])
    images_with_alt = sum(1 for img in images if img.get("has_alt"))

    price_strs = [p.get("price", "") for p in prices[:10]] if prices and isinstance(prices[0], dict) else [str(p) for p in prices[:10]]

    social_lines = "\n".join(f"  - {k}: {v}" for k, v in socials.items()) if socials else "  None found"

    return f"""Audit this website and generate a structured brand audit.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEBSITE: {url}
BRAND NAME: {brand_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTACT INFO:
  Phones: {", ".join(phones) if phones else "None found"}
  Emails: {", ".join(emails) if emails else "None found"}
  Addresses: {", ".join(addresses) if addresses else "None found"}

SOCIAL PROFILES:
{social_lines}

WEBSITE CONTENT:
  Meta title: "{meta_title}"
  Meta description: "{meta_desc}"
  H1 tags: {h1s[:3]}
  Services identified: {len(services)} → {services[:8]}
  Prices found: {price_strs[:8] if price_strs else "None"}
  Team members: {team[:5] if team else "None"}
  CTA buttons: {ctas[:6] if ctas else "None"}
  Text length: {text_length} characters
  Mobile responsive: {"Yes" if has_mobile else "No"}
  Images: {len(images)} total, {images_with_alt} with alt text

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS:
1. brand_summary: 3-6 bullets describing what the business offers and who it serves.
   Reference specific services/team/location evidence from above.
2. positioning_guess: 1-2 sentences describing how this brand positions itself in the
   market (premium? budget? local expert? etc.). Cite evidence.
3. conversion_notes: 3-6 bullets analysing conversion readiness.
   Each bullet MUST reference at least one specific data point (CTA count, pricing,
   team presence, mobile responsiveness, content volume, etc.).
4. top_recommendations: 3-6 prioritised actions. Each action MUST include
   "because …" referencing a specific weakness from the data above.

REQUIRED JSON FORMAT:
{{
  "brand_summary": [
    "Bullet 1 referencing specific services/team",
    "Bullet 2 with evidence",
    "Bullet 3"
  ],
  "positioning_guess": "1-2 sentences citing evidence from the data.",
  "conversion_notes": [
    "Note 1 referencing specific CTA / pricing / mobile data",
    "Note 2",
    "Note 3"
  ],
  "top_recommendations": [
    "Action 1 because [specific weakness from data]",
    "Action 2 because [specific weakness from data]",
    "Action 3 because [specific weakness from data]"
  ]
}}

Be specific, be harsh where needed, and always tie every bullet to the evidence above."""


def _parse_audit(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(l for l in lines if not l.startswith("```")).strip()

    data = json.loads(content)
    return {
        "brand_summary": data.get("brand_summary", []),
        "positioning_guess": data.get("positioning_guess", ""),
        "conversion_notes": data.get("conversion_notes", []),
        "top_recommendations": data.get("top_recommendations", []),
    }


def _empty_audit() -> dict:
    return {
        "brand_summary": [],
        "positioning_guess": "",
        "conversion_notes": [],
        "top_recommendations": [],
    }
