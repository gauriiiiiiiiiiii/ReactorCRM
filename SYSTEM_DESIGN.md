# LinkedIn Lead Identification System — Full System Design

## 1. Problem Statement

Identify LinkedIn posts relevant to a target audience (e.g. startup founders, MBA students,
entrepreneurship programme applicants) and surface the people who have genuinely engaged
with those posts as warm leads for outreach.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         USER / OPERATOR                              │
│           Adds LinkedIn post URLs via Web Dashboard                  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTP (Flask)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    WEB APPLICATION (Flask)                           │
│   Routes: Dashboard · Posts · Leads · Export · JSON API             │
└──────────┬─────────────────────────────────────────┬────────────────┘
           │ Triggers background thread              │ Reads/writes
           ▼                                         ▼
┌─────────────────────────┐              ┌───────────────────────────┐
│   SCRAPE ORCHESTRATOR   │              │      DATABASE (SQLite)    │
│   leads/extractor.py    │◄────────────►│  TrackedPost · Lead       │
└─────────┬───────────────┘              └───────────┬───────────────┘
          │ async Playwright                          │
          ▼                                           │
┌─────────────────────────┐              ┌────────────▼──────────────┐
│  LINKEDIN SCRAPER       │              │   LEAD SCORING ENGINE     │
│  scraper/linkedin_      │              │   leads/scorer.py         │
│  scraper.py             │              │   Score: 0-100            │
│  · Login / cookies      │              │   Tier: Hot/Warm/Cold     │
│  · Post metadata        │              └───────────────────────────┘
│  · Reactors (likers)    │
│  · Commenters           │              ┌───────────────────────────┐
└─────────────────────────┘              │   EXPORT ENGINE           │
                                         │   leads/exporter.py       │
                                         │   CSV · Excel (styled)    │
                                         └───────────────────────────┘
```

---

## 3. Data Flow

```
1. User submits LinkedIn post URL
       │
2. TrackedPost record created (status=pending)
       │
3. Background thread spawns async scraper
       │
       ├─── scrape_post_metadata()   → author, counts
       │
       ├─── scrape_post_reactors()   → list of {name, headline, reaction_type, profile_url}
       │
       └─── scrape_post_commenters() → list of {name, headline, comment_text, profile_url}
              │
4. Each profile → score_lead() → score (0-100) + breakdown JSON
       │
5. Lead records saved to SQLite
       │
6. TrackedPost.status → "done"
       │
7. Dashboard auto-polls via /api/posts/{id}/status every 5s
       │
8. User views/filters leads, updates CRM status, exports CSV/Excel
```

---

## 4. Lead Scoring Model

Scores range **0–100**. Tier thresholds: Hot ≥70, Warm 45-69, Cold <45.

| Signal | Max Points | Rationale |
|--------|-----------|-----------|
| Engagement type: comment | 40 | Comments require effort; high intent |
| Engagement type: repost | 25 | Sharing = endorsement |
| Engagement type: like | 10 | Lowest effort but still interested |
| Reaction quality (Insightful > Love > Like) | 0–8 | Insightful = professional interest |
| Connection degree (1st > 2nd > 3rd) | 5–15 | Closer connections = warmer lead |
| Comment keyword match | 0–25 | "interested", "apply", "DM", "register" |
| ICP headline match | 0–12 | "founder", "CEO", "investor", "MBA" |

---

## 5. LinkedIn API Limitations

### Official LinkedIn APIs
| API | Access | Can Get Post Engagements? |
|-----|--------|--------------------------|
| LinkedIn Marketing API | App approval required | ✅ (for own Sponsored Content only) |
| LinkedIn Pages API | Company page admins | ✅ (own page posts) |
| LinkedIn Member Data Portability API | Individual users | ❌ (own data only) |
| LinkedIn Sign In with LinkedIn | OAuth apps | ❌ (profile data only) |

**Key restrictions:**
- No official API endpoint to get likers/commenters of arbitrary posts
- Rate limits: 100 calls/day for most endpoints; 500/day for marketing
- Must be the post author or have explicit permission
- Scraping violates LinkedIn ToS (section 8.2) — use only with your own session / legitimate authorization

### Practical implication
The **only compliant path** for third-party posts is:
1. Use your own LinkedIn account session (Playwright automation — grey area)
2. Use authorized third-party data vendors (Proxycurl, Phantom Buster, etc.)
3. Ask the post author to share engagement data directly

---

## 6. Tools & Platforms

### Free / Open Source
| Tool | Purpose |
|------|---------|
| Playwright (Python) | Browser automation, LinkedIn scraping with user session |
| Flask + SQLAlchemy | Web app + ORM |
| Pandas / openpyxl | Data export to CSV / Excel |
| SQLite | Local database (zero config) |
| BeautifulSoup4 | HTML parsing fallback |

### Paid / Commercial Alternatives
| Tool | Cost | Purpose |
|------|------|---------|
| **Proxycurl API** | $0.01–$0.03 / profile | Compliant LinkedIn profile enrichment |
| **PhantomBuster** | $56/mo | LinkedIn automation flows (post likers, commenters) |
| **Apify LinkedIn Scraper** | Pay-per-result | Cloud scraping actors |
| **Expandi / Dripify** | $99/mo | LinkedIn outreach + lead extraction |
| **Lusha / Apollo.io** | $49-$99/mo | Lead enrichment with emails |
| **LinkedIn Sales Navigator** | $99/mo | Advanced search + lead lists |

---

## 7. Approaches Used by Other Companies

### A. Ghost Profile Enrichment (Proxycurl model)
Aggregate publicly visible LinkedIn data via official + unofficial data partnerships.
No direct scraping; uses cached/crawled data stored in their own DB.

### B. Session-based Automation (PhantomBuster model)
User connects their own LinkedIn cookie. Phantom runs scripts server-side using the user's
identity — stays within LinkedIn's per-user rate limits.

### C. Chrome Extension + Background Sync (Dux-Soup model)
A browser extension captures engagement data as the user naturally browses LinkedIn,
syncing to a CRM without triggering anti-bot detection.

### D. Official API + Webhooks (for own company pages)
Companies owning LinkedIn Pages use the Pages API to get real-time engagement data
on their own posts. Fully compliant but limited to owned content.

### E. AI-enriched Intent Signals (Clay.com model)
Combine LinkedIn engagement data with company job postings, news signals,
and website traffic to build a multi-signal intent score. Outreach is triggered
when intent score crosses a threshold.

---

## 8. Ethical & Legal Considerations

1. **LinkedIn ToS** — Automated scraping without authorization is a ToS violation.
   For a production system, use Proxycurl or LinkedIn's Marketing API.
2. **GDPR / DPDP** — Profiling EU/Indian citizens for commercial outreach requires
   a lawful basis. Add opt-out and data deletion flows.
3. **Rate Limiting** — This system enforces 2–5 second random delays to avoid
   hammering LinkedIn servers and protect the user's account.
4. **Session Safety** — Never share credentials; run with `HEADLESS_BROWSER=false`
   to manually solve CAPTCHAs when they appear.

---

## 9. Scaling Path

| Stage | Solution |
|-------|---------|
| 1 person, <10 posts/day | This repo (Flask + SQLite + Playwright) |
| Team of 5, 100 posts/day | Replace SQLite → PostgreSQL; add task queue (Celery + Redis) |
| Enterprise, 1000+ posts/day | Proxycurl API + Apache Kafka for event streaming + Elasticsearch for lead search |
| With CRM integration | Webhooks to HubSpot / Salesforce when lead score > threshold |
