# MERIDIAN
### Multi-Agent Corporate Intelligence & Due Diligence Platform
*Elasticsearch Agent Builder Hackathon 2026*

---

## What Is MERIDIAN?

MERIDIAN is a multi-agent AI system that investigates companies in minutes — the way a world-class intelligence analyst would in weeks.

When you need to evaluate a potential partner, investment, or vendor, MERIDIAN deploys **7 specialized agents in parallel** to cross-reference corporate registries, financial filings, court records, sanctions lists, and news — then synthesizes everything into a clear risk report with a recommendation.

**Demo target:** Try `"Nexus Global Holdings"` — a fictional company with hidden offshore structure, SEC investigation, Ponzi scheme allegations, and a CEO with a history of failed funds.

---

## Architecture

```
User Input: "Investigate Nexus Global Holdings"
                        │
              ┌─────────▼──────────┐
              │   ORCHESTRATOR     │  ← Coordinates all agents
              └────────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
   │ Entity  │    │Financial│   │ Legal   │
   │Discovery│    │ Signal  │   │Intelli- │
   │ Agent   │    │ Agent   │   │  gence  │
   └─────────┘    └─────────┘   └─────────┘
        │              │              │
   ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
   │Executive│    │Sentiment│   │  Geo &  │
   │Backgrnd │    │Narrative│   │Jurisd.  │
   │ Agent   │    │ Agent   │   │ Agent   │
   └─────────┘    └─────────┘   └─────────┘
                       │
              ┌────────▼───────────┐
              │  RISK SYNTHESIS    │  ← Final reasoning + report
              │     AGENT          │
              └────────────────────┘
                       │
              ┌────────▼───────────┐
              │  FINAL REPORT      │
              │  Risk Score 8.9/10 │
              │  Risk Level: HIGH  │
              │  Recommendation:   │
              │  DO NOT PROCEED    │
              └────────────────────┘
```

### Elasticsearch Features Used

| Feature | Where Used |
|---|---|
| **Hybrid Search (BM25 + vector)** | Entity name resolution, fuzzy company matching |
| **ES\|QL** | Sentiment trends, financial time-series, legal aggregation, geo breakdown |
| **Dense Vector / kNN** | Semantic similarity of legal cases, news content matching |
| **Geo Queries** | Jurisdiction risk mapping, offshore structure detection |
| **Time-Series Analytics** | Financial trends, sentiment shifts, news volume spikes |
| **Nested Documents** | Employment history, agent findings per investigation |
| **Aggregations** | Risk scoring across multiple data dimensions |

---

## Quick Start

### 1. Start Elasticsearch + Kibana
```bash
docker-compose up -d
```
Wait ~30s for Elasticsearch to be ready.

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.template .env
# Edit .env with your Anthropic API key
# ES_URL defaults to http://localhost:9200 (local Docker)
```

### 4. Set up indices + load demo data
```bash
python scripts/setup_indices.py
python scripts/demo_loader.py
```

### 5. Start the API
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run an investigation
```bash
# Streaming (real-time events)
curl -X POST http://localhost:8000/investigate/stream \
     -H "Content-Type: application/json" \
     -d '{"target": "Nexus Global Holdings"}' \
     --no-buffer

# Or full report (wait for completion)
curl -X POST http://localhost:8000/investigate \
     -H "Content-Type: application/json" \
     -d '{"target": "Nexus Global Holdings"}'
```

---

## Ingest Real Data

```bash
# Ingest real company data from SEC, GDELT, CourtListener
python scripts/ingest_real_data.py --company "Enron" --cik 72971

# Load OFAC sanctions list (full SDN list, ~7000 entries)
python scripts/ingest_real_data.py --sanctions
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/investigate/stream` | Streaming SSE investigation |
| `POST` | `/investigate` | Sync investigation (wait for report) |
| `GET` | `/investigations/{id}` | Get past investigation |
| `GET` | `/investigations` | List all investigations |
| `GET` | `/search/entities?q=name` | Search entities |
| `POST` | `/esql` | Run ES\|QL query directly |

---

## The 7 Agents

1. **Entity Discovery** — Maps the full corporate ownership structure, finds subsidiaries and related entities
2. **Financial Signal** — Analyzes SEC filings for going concern warnings, auditor changes, financial restatements
3. **Legal Intelligence** — Searches court records, regulatory actions, sanctions lists (OFAC/EU/UN)
4. **Executive Background** — Profiles executives, detects PEP status, prior failed companies, conflicts of interest
5. **Sentiment & Narrative** — Time-series sentiment analysis, detects narrative shifts and news volume spikes
6. **Geo & Jurisdiction** — Maps offshore exposure, flags sanctioned country presence, data sovereignty risk
7. **Risk Synthesis** — Collects all findings, identifies cross-agent patterns, generates weighted risk score + recommendation

---

## Data Sources (All Free, No API Key)

| Source | Data | API |
|--------|------|-----|
| SEC EDGAR | US company filings, financials | `data.sec.gov` |
| GDELT | Global news (65 languages) | `api.gdeltproject.org` |
| CourtListener | US federal court records | `courtlistener.com/api` |
| OFAC SDN | US Treasury sanctions list | `treasury.gov` |
| OpenCorporates | Global corporate registry | `opencorporates.com` |

---

## License

MIT License — Open Source for the Hackathon
