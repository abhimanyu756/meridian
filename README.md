# MERIDIAN
### Multi-Agent Corporate Intelligence & Due Diligence Platform
*Elasticsearch Agent Builder Hackathon 2026*

---

## What Is MERIDIAN?

MERIDIAN is a multi-agent AI system that investigates companies in minutes — the way a world-class intelligence analyst would in weeks.

When you need to evaluate a potential partner, investment, or vendor, MERIDIAN deploys **7 specialized agents in parallel** to cross-reference corporate registries, financial filings, court records, sanctions lists, and news — then synthesizes everything into a clear risk report with a recommendation.

**Demo targets:** Try `"Nexus Global Holdings"` (CRITICAL risk — offshore shell companies, Ponzi scheme allegations) or `"Tesla"` (real SEC/news data).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MERIDIAN PLATFORM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    SSE Stream    ┌────────────────────────────────┐  │
│  │ Frontend  │◄───────────────►│   FastAPI Server               │  │
│  │ (HTML/JS) │                 │   - /investigate/stream (SSE)  │  │
│  │           │                 │   - /search/semantic (kNN)     │  │
│  └──────────┘                  │   - /esql (ES|QL proxy)        │  │
│                                │   - /investigations (CRUD)     │  │
│                                └────────────┬───────────────────┘  │
│                                             │                       │
│                              ┌──────────────▼──────────────┐       │
│                              │     ORCHESTRATOR            │       │
│                              │  (Parallel Agent Execution)  │       │
│                              └──────────────┬──────────────┘       │
│                                             │                       │
│           ┌─────────────────────────────────┼───────────────┐      │
│           │              Phase 1            │               │      │
│   ┌───────▼────────┐              ┌────────▼─────────┐     │      │
│   │ Entity Discovery│   Phase 2   │ Batch 1 (parallel)│     │      │
│   │ (Corporate      │──────────►  │ ┌───────────────┐│     │      │
│   │  Structure)     │              │ │Financial Signal││     │      │
│   └────────────────┘              │ │Legal Intel     ││     │      │
│                                    │ │Executive Bkgnd ││     │      │
│                                    │ └───────────────┘│     │      │
│                                    │ Batch 2 (parallel)│     │      │
│                                    │ ┌───────────────┐│     │      │
│                                    │ │Sentiment      ││     │      │
│                                    │ │Geo/Jurisdiction││     │      │
│                                    │ └───────────────┘│     │      │
│                                    └──────────────────┘     │      │
│           │                                                 │      │
│           └──────────────┬──────────────────────────────────┘      │
│                          │ Phase 3                                  │
│               ┌──────────▼──────────┐                              │
│               │  Risk Synthesis     │  ← Weighted cross-agent      │
│               │  Agent              │    reasoning + final report   │
│               └──────────┬──────────┘                              │
│                          │                                          │
│               ┌──────────▼──────────────────────────────────┐      │
│               │  ELASTICSEARCH (6 Custom Indices)            │      │
│               │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │      │
│               │  │ entities │ │ filings  │ │  legal   │    │      │
│               │  └──────────┘ └──────────┘ └──────────┘    │      │
│               │  ┌──────────┐ ┌──────────┐ ┌──────────────┐│      │
│               │  │   news   │ │executives│ │investigations││      │
│               │  └──────────┘ └──────────┘ └──────────────┘│      │
│               └─────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Elasticsearch Features Used

| Feature | Where Used | Details |
|---------|-----------|---------|
| **ES\|QL Analytics** | All specialist agents | `STATS`, `EVAL`, `DATE_TRUNC`, `SUM(CASE(...))` for time-series analytics |
| **Hybrid Search** (BM25 + fuzzy) | Entity Discovery | Match companies by name, aliases, fuzzy keyword matching |
| **kNN Vector Search** | `/search/semantic` endpoint | `dense_vector` (384 dims, cosine) for semantic news search |
| **Geo Queries** | Geo & Jurisdiction agent | `geo_point` fields for mapping corporate structure |
| **Nested Documents** | Executive employment history | Complex nested search on employment records |
| **Aggregations** | Sentiment, Geo agents | `terms`, `geo_centroid` aggregations |
| **6 Custom Index Schemas** | All agents | Purpose-built mappings with dense_vector, geo_point, nested, keyword, text |

---

## The 7 Agents

| # | Agent | ES Queries Used | Risk Focus |
|---|-------|----------------|------------|
| 1 | **Entity Discovery** | Hybrid BM25+fuzzy search, term queries | Corporate structure, shell companies, subsidiaries |
| 2 | **Financial Signal** | ES\|QL: `esql_financial_trend`, `esql_auditor_changes` | Going concern warnings, restatements, debt spirals |
| 3 | **Legal Intelligence** | ES\|QL: `esql_legal_exposure` | Court records, sanctions, regulatory penalties |
| 4 | **Executive Background** | Nested employment history search | PEP screening, serial failures, conflicts of interest |
| 5 | **Sentiment & Narrative** | ES\|QL: `esql_sentiment_trend`, `esql_news_volume_spike` | News sentiment shifts, PR manipulation, media crises |
| 6 | **Geo & Jurisdiction** | ES\|QL: `esql_geo_risk`, geo aggregations | Offshore exposure, sanctioned countries, tax havens |
| 7 | **Risk Synthesis** | Cross-agent weighted analysis | Final risk score, executive summary, recommendation |

---

## Tech Stack

- **Elasticsearch 9.x** on Elastic Cloud — ES|QL, dense_vector, geo_point, nested fields
- **Gemini 2.5 Flash** — AI reasoning engine for each agent (`google-genai` SDK)
- **FastAPI** — Async Python backend with Server-Sent Events (SSE) streaming
- **Vanilla JS/HTML/CSS** — Zero-dependency frontend with real-time agent tracking

---

## Quick Start

### Prerequisites
- Python 3.11+
- Elasticsearch Cloud instance (or local ES 9.x)
- Google Gemini API key (free tier works)

### 1. Install dependencies
```bash
cd meridian
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file:
```env
ES_URL=https://your-es-cloud-url:443
ES_API_KEY=your-elasticsearch-api-key
ANTHROPIC_API_KEY=your-gemini-api-key
```

### 3. Load data
```bash
python scripts/ingest_all.py
```
This loads:
- **Real data** from SEC EDGAR (financial filings) and GDELT (global news) for 6 real companies
- **Rich synthetic data** for 6 fictional companies across all risk levels (LOW to CRITICAL)

### 4. Start the server
```bash
python run.py
```

### 5. Open the UI
Navigate to **http://localhost:8000/app/** in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/investigate/stream` | Start investigation with real-time SSE streaming |
| `POST` | `/investigate` | Start investigation (synchronous, wait for full report) |
| `GET` | `/investigations` | List all past investigations |
| `GET` | `/investigations/{id}` | Get specific investigation by ID |
| `DELETE` | `/investigations/{id}` | Delete a specific investigation |
| `DELETE` | `/investigations` | Clear all investigations |
| `POST` | `/search/semantic` | Semantic vector search (kNN) across news |
| `POST` | `/esql` | Execute ES\|QL queries directly |
| `GET` | `/search/entities?q=...` | Search entities by name (hybrid search) |
| `GET` | `/health` | Health check |

---

## Sample Companies

### Synthetic (Full Risk Spectrum)
| Company | Risk Level | Key Risks |
|---------|-----------|-----------|
| Nexus Global Holdings | CRITICAL | Offshore BVI structure, SEC investigation, Ponzi allegations |
| Crimson Meridian Capital | CRITICAL | Cayman Islands fund, sanctions violations, criminal charges |
| Pacific Rim Trading Corp | HIGH | Panama subsidiaries, OFAC sanctions, regulatory actions |
| Zenith Defense Solutions | MEDIUM-HIGH | Government contracts, whistleblower complaints |
| OmniVault Technologies | MEDIUM | Rapid growth startup, some IP litigation |
| Aurora Health Systems | LOW | Clean record, strong compliance, well-regulated |

### Real Companies (SEC EDGAR + GDELT Data)
Tesla, Meta Platforms, Wells Fargo, Boeing, Goldman Sachs, ExxonMobil

---

## Data Indices

```
meridian-entities        — Corporate entities with ownership structure & geo_point
meridian-filings         — SEC filings with financial metrics & content_vector
meridian-legal           — Court records, sanctions, regulatory actions
meridian-news            — News articles with sentiment scores & content_vector
meridian-executives      — Executive profiles with nested employment history
meridian-investigations  — Investigation results, agent findings, risk reports
```

All indices include `dense_vector` fields (384 dimensions, cosine similarity) for semantic search capabilities.

---

## Key Features

- **Real-time streaming** — Watch agents work in real-time via SSE
- **Parallel agent execution** — 5 specialist agents run in parallel batches
- **Download report** — Export investigation results as a text file
- **Investigation history** — Browse and reload past investigations
- **Semantic search** — kNN vector search across news articles
- **Live data stats** — Homepage shows real-time index counts from ES|QL
- **Risk gauge** — Animated visual risk score with color-coded severity

---

## License

MIT License — Built for the Elasticsearch Agent Builder Hackathon 2026.
