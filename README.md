# Universal Business Intelligence Scraper

A complete Python Flask backend that scrapes and analyses businesses from **any niche** using 100 % free tools.

## Features

- **Google Maps Scraper** – extracts name, rating, reviews, address, phone, website, and hours
- **Website Scraper** – finds services, prices, and team members from business websites
- **Instagram Scraper** – retrieves public profile stats using the free [instaloader](https://instaloader.github.io/) library
- **AI Revenue Analysis** – leverages the free [Groq API](https://console.groq.com) (14,400 req/day) to produce structured insights
- **Universal Niche Support** – medspas, restaurants, dentists, gyms, salons, lawyers, accountants, real estate, and more
- **REST API** – Flask endpoints with CORS for easy frontend integration
- **SQLite Database** – stores all results via SQLAlchemy

---

## Grading Rubrics & Score Distribution

### Website Grader (`app/analyzers/website_grader.py`)

Websites are scored on a **0–100 scale** using a 20-item rubric (0/1/2 per item, max 40 raw points, scaled to 100).
The score is deliberately spread across the full range to make sites meaningfully differentiable:

| Score Band | Meaning |
|------------|---------|
| 0–40 | Missing SSL **or** mobile viewport — major technical gaps |
| 41–55 | SSL + mobile present but no CTAs and no pricing |
| 56–70 | SSL + mobile + CTAs + pricing, but missing schema / team info |
| 71–90 | All major signals present (SSL, mobile, CTAs, pricing, team, schema) |
| 91–100 | Near-perfect: every signal present with strong content depth |

**Rubric sections:**
- **A – Conversion & Offer Clarity (12 pts):** CTA labels, appointment path, pricing transparency, service pages, objection handling, message consistency
- **B – Trust & Authority (10 pts):** Named team members, reviews/testimonials, results proof, risk reducers, policies
- **C – Local SEO & Structure (10 pts):** Local intent keywords, dedicated service pages, internal links, schema markup (LocalBusiness/Service), NAP
- **D – Technical & UX (8 pts):** Mobile viewport, SSL/HTTPS, image alt text coverage, content depth

Every item's `evidence` field must cite concrete data points (e.g. exact CTA labels, image counts, schema types, price counts).
`strengths`, `weaknesses`, and `recommendations` each contain **exactly 3 entries** tied to observed signals.

---

### Business AI Analyzer (`app/analyzers/ai_analyzer.py`)

`service_quality_score` spans **3.0–9.5** using clearly defined bands:

| Band | Score | Criteria |
|------|-------|----------|
| Poor | 3.0–4.4 | Rating <3.5 or <5 reviews AND no pricing AND no team |
| Below average | 4.5–5.9 | Rating 3.5–3.9, few reviews, sparse info |
| Average | 6.0–7.0 | Rating 4.0–4.2, 10–49 reviews, some info |
| Good | 7.1–8.0 | Rating 4.3–4.6, 50–199 reviews, pricing or team visible |
| Very good | 8.1–9.0 | Rating 4.7–4.8, 200+ reviews, pricing AND team visible |
| Excellent | 9.1–9.5 | Rating 4.9–5.0, 500+ reviews, full info + strong social |

The `service_quality_reasoning` field always cites the specific rating, review count, pricing status, team size, and social presence.

---

### Opportunity Score & Lead Ranking (`app/analyzers/lead_ranker.py`)

The **opportunity score** (0–100) measures how attractive a business is for marketing outreach.  
It is calculated from the following factors:

| Factor | Signal | Points |
|--------|--------|--------|
| Website quality (inverted) | Terrible site (<40) = large gap to fix | up to +25 |
| Business health | Rating ≥4.5 + ≥50 reviews | up to +20 |
| Social followers | >5,000 followers = digital-aware client | up to +12 |
| Social engagement rate | ≥4% engagement = responsive audience | up to +6 |
| Pricing transparency | No pricing shown = clear improvement to sell | +8 |
| Team size | ≥3 members = larger budget | up to +10 |
| Service breadth | ≥5 services listed | +5 |
| Website sweet spot | Has website scoring 30–60 | +15 |

**Lead ranking** sorts businesses into three buckets:
1. Qualified + non-excellent website (best prospects)
2. Qualified + excellent website (deprioritised — less to improve)
3. Not qualified

Within each bucket, ties are broken deterministically by: opportunity score → reviews count → rating → website score (ascending).

---

## Project Structure

```
/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration (reads .env)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models.py            # ORM models (Business, InstagramData, Analysis)
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── google_maps.py   # Playwright-based Google Maps scraper
│   │   ├── website.py       # Playwright + BS4 website scraper
│   │   ├── instagram.py     # instaloader Instagram scraper
│   │   └── utils.py         # Shared helpers
│   ├── analyzers/
│   │   ├── __init__.py
│   │   └── ai_analyzer.py   # Groq API integration
│   ├── niches/
│   │   ├── __init__.py
│   │   └── config.json      # Niche-specific configuration
│   └── routes/
│       ├── __init__.py
│       └── analyze.py       # API blueprints
├── run.py                   # Entry point
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/smaduri2008/business-scraper.git
cd business-scraper
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Get a free Groq API key

1. Go to <https://console.groq.com>
2. Sign up for a free account
3. Create an API key in the dashboard

### 5. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_actual_key
```

### 6. Run the server

```bash
python run.py
```

The API will be available at `http://localhost:5000`.

---

## API Endpoints

### `GET /api/health`

Returns server status.

```bash
curl http://localhost:5000/api/health
```

```json
{"status": "ok", "timestamp": "2024-01-15T12:00:00.000000"}
```

---

### `GET /api/niches`

Returns all supported niche configurations.

```bash
curl http://localhost:5000/api/niches
```

```json
{
  "medspas": {
    "label": "Medical Spas",
    "common_services": ["Botox", "Dermal Fillers", "Laser Hair Removal"]
  }
}
```

---

### `POST /api/analyze`

Main endpoint – scrapes, analyses, and persists business data.

**Request:**

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"niche": "medspas", "location": "Miami, FL", "max_results": 5}'
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `niche` | string | ✅ | – | Business niche key (see `/api/niches`) |
| `location` | string | ✅ | – | City, state, or address |
| `max_results` | integer | ❌ | 10 | Number of businesses (1–50) |

**Response:**

```json
{
  "niche": "medspas",
  "location": "Miami, FL",
  "results_count": 5,
  "processing_time_seconds": 42.5,
  "businesses": [
    {
      "name": "Glow Med Spa",
      "niche": "medspas",
      "location": "Miami, FL",
      "rating": 4.8,
      "reviews_count": 312,
      "address": "123 Ocean Dr, Miami, FL 33139",
      "phone": "(305) 555-0123",
      "website": "https://glowmedspa.com",
      "hours": "Mon-Sat 9am-7pm",
      "services": ["Botox", "Dermal Fillers", "HydraFacial"],
      "prices": ["$150", "$299", "$499"],
      "team_members": ["Dr. Sofia Alvarez MD", "Rebecca Torres RN"],
      "instagram": {
        "username": "glowmedspa",
        "followers": 8200,
        "following": 420,
        "posts": 315,
        "engagement_rate": 3.14,
        "bio": "Miami's premier medical spa ✨",
        "is_verified": false,
        "is_business": true
      },
      "analysis": {
        "revenue_streams": ["Injectable treatments", "Laser services", "Skincare retail"],
        "estimated_revenue_tier": "High",
        "pricing_strategy": "Premium",
        "service_quality_score": 8.5,
        "competitive_assessment": "Strong online presence and high review count indicate market leadership.",
        "niche_specific_insights": "Botox and filler services are primary revenue drivers with consistent demand."
      }
    }
  ]
}
```

---

## Frontend Integration

```javascript
async function analyzeBusinesses(niche, location, maxResults = 10) {
  const response = await fetch('http://localhost:5000/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ niche, location, max_results: maxResults }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Analysis failed');
  }

  return response.json();
}

// Usage
const data = await analyzeBusinesses('dentists', 'Austin, TX', 5);
console.log(data.businesses);
```

---

## Adding New Niches

Edit `app/niches/config.json` and add a new entry:

```json
{
  "veterinarians": {
    "label": "Veterinary Clinics",
    "service_terms": ["pet", "animal", "veterinary", "dog", "cat", "surgery", "vaccine"],
    "common_services": ["Wellness Exams", "Vaccinations", "Surgery", "Dental Cleaning", "Emergency Care"]
  }
}
```

The new niche is immediately available via `/api/niches` and `/api/analyze`.

---

## Deployment (Free Options)

### Render.com

1. Connect your GitHub repository
2. Set environment variables in the Render dashboard
3. Build command: `pip install -r requirements.txt && playwright install chromium`
4. Start command: `python run.py`

### Railway.app

```toml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "playwright install chromium && python run.py"
```

### Fly.io

```bash
fly launch
fly secrets set GROQ_API_KEY=your_key
fly deploy
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `playwright._impl._api_types.Error: Executable doesn't exist` | Run `playwright install chromium` |
| `ModuleNotFoundError: No module named 'instaloader'` | Run `pip install instaloader` |
| `Groq API returns 401` | Check that `GROQ_API_KEY` is correctly set in `.env` |
| Google Maps returns 0 results | Try a broader location string, e.g. `"New York"` instead of a zip code |
| Instagram profile not found | The business may not have a public Instagram; the scraper will skip it gracefully |

---

## Rate Limiting

The scrapers include built-in delays (`1.5–2.5 s` between requests) to respect server limits.
For large-scale use, consider running in batches and caching results in the SQLite database.

---

## License

MIT
