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
