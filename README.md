# LinkedIn Lead Identification System

A full-stack web application to identify, score, and manage leads from LinkedIn post engagements.

## Features

- **Post Tracker** — add any LinkedIn post URL and auto-scrape likers + commenters
- **Lead Scoring** — 0-100 score based on engagement type, reaction quality, comment keywords, ICP signals
- **Lead Tiers** — Hot (70+) / Warm (45-69) / Cold (<45) with color-coded UI
- **CRM Lite** — update lead status (new → contacted → qualified → converted), add notes/email
- **Export** — download leads as CSV or styled Excel spreadsheet
- **Live Status** — dashboard auto-polls scraping progress every 5 seconds
- **REST API** — `/api/posts` and `/api/leads` JSON endpoints

---

## Quick Start

### 1. Install dependencies
```bash
cd linkedin-lead-system
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure credentials
```bash
cp .env.example .env
# Edit .env with your LinkedIn email/password
```

### 3. Run with demo data (no LinkedIn login needed)
```bash
python seed_demo.py   # seeds realistic fake data
python app.py         # starts server on http://127.0.0.1:5000
```

### 4. Run with live scraping
```bash
python app.py
# Open http://127.0.0.1:5000/posts
# Paste a LinkedIn post URL and click "Start Tracking"
```

---

## Project Structure

```
linkedin-lead-system/
├── app.py                      # Flask app + routes
├── config.py                   # Config from .env
├── seed_demo.py                # Demo data seeder
├── database/
│   └── models.py               # TrackedPost + Lead SQLAlchemy models
├── scraper/
│   └── linkedin_scraper.py     # Playwright-based scraper
├── leads/
│   ├── extractor.py            # Orchestrates scrape → save pipeline
│   ├── scorer.py               # 0-100 lead scoring engine
│   └── exporter.py             # CSV / Excel export
├── templates/                  # Jinja2 HTML templates
├── static/css/style.css        # Full UI stylesheet
├── static/js/app.js            # Status polling + UX
├── exports/                    # Generated CSV/Excel files
├── SYSTEM_DESIGN.md            # Full system design document
└── .env.example                # Environment variable template
```

---

## Scoring Model

| Signal | Weight |
|--------|--------|
| Comment | 40 pts |
| Repost | 25 pts |
| Like | 10 pts |
| Reaction type (Insightful best) | +0–8 pts |
| 1st connection | +15 pts |
| Comment intent keywords | +0–25 pts |
| ICP profile match (founder/CEO/investor) | +0–12 pts |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/posts` | All tracked posts (JSON) |
| GET | `/api/posts/{id}/status` | Scraping status + lead count |
| GET | `/api/leads?post_id=N` | Leads for a post (JSON) |

---

## LinkedIn API Note

LinkedIn's official API **does not** expose post likers/commenters for arbitrary posts.
This tool uses Playwright browser automation with your own LinkedIn session.
For production use, consider:
- **Proxycurl** (compliant profile enrichment API)
- **PhantomBuster** (LinkedIn automation with user's own session)
- **LinkedIn Marketing API** (if you own the posts / pages)

See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for the full architecture, limitations, and scaling path.
