"""
SEC EDGAR Ingester
Pulls company filings from the free SEC EDGAR API (no API key required).
API docs: https://efts.sec.gov/LATEST/search-index?q=&dateRange=custom
"""
import httpx
import asyncio
from datetime import datetime, timezone
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()

EDGAR_BASE = "https://efts.sec.gov"
EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"

HEADERS = {
    "User-Agent": "MERIDIAN hackathon@meridian-intelligence.io",
    "Accept-Encoding": "gzip, deflate",
}


async def search_company(name: str) -> list[dict]:
    """Search for a company on EDGAR by name."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        resp = await client.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": name, "dateRange": "custom", "category": "form-type"},
        )
        resp.raise_for_status()
        return resp.json().get("hits", {}).get("hits", [])


async def get_company_facts(cik: str) -> dict:
    """Get company financial facts from SEC."""
    cik_padded = cik.zfill(10)
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        resp = await client.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json")
        if resp.status_code == 200:
            return resp.json()
        return {}


async def get_submissions(cik: str) -> dict:
    """Get all filings for a company."""
    cik_padded = cik.zfill(10)
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        resp = await client.get(f"{EDGAR_SUBMISSIONS}/CIK{cik_padded}.json")
        if resp.status_code == 200:
            return resp.json()
        return {}


async def ingest_company(company_name: str, cik: str):
    """Full ingestion pipeline for a company from EDGAR."""
    es = get_es_client()

    submissions = await get_submissions(cik)
    facts = await get_company_facts(cik)

    company_info = {
        "entity_id": f"sec-{cik}",
        "name": submissions.get("name", company_name),
        "entity_type": "company",
        "jurisdiction": "US",
        "sic_codes": [str(submissions.get("sic", ""))],
        "data_sources": ["SEC EDGAR"],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await es.index(
        index=settings.index_entities,
        id=f"sec-{cik}",
        document=company_info,
    )

    # Ingest recent filings
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    descriptions = recent.get("primaryDocument", [])

    annual_forms = {"10-K", "10-K405", "10-KSB", "20-F", "40-F"}

    for i, (form, date) in enumerate(zip(forms, dates)):
        if form in annual_forms:
            # Extract financial data from facts if available
            revenue = _extract_fact(facts, "Revenues", date)
            net_income = _extract_fact(facts, "NetIncomeLoss", date)
            total_assets = _extract_fact(facts, "Assets", date)

            filing_doc = {
                "filing_id": f"sec-{cik}-{i}",
                "entity_id": f"sec-{cik}",
                "entity_name": company_info["name"],
                "filing_type": form,
                "filing_date": date,
                "revenue": revenue,
                "net_income": net_income,
                "total_assets": total_assets,
                "source": "SEC EDGAR",
                "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            await es.index(
                index=settings.index_filings,
                id=f"sec-{cik}-{i}",
                document=filing_doc,
            )

    print(f"  Ingested SEC EDGAR data for {company_info['name']} (CIK: {cik})")


def _extract_fact(facts: dict, concept: str, date: str) -> float | None:
    """Extract a specific financial fact for a given period."""
    try:
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        concept_data = us_gaap.get(concept, {}).get("units", {}).get("USD", [])
        for entry in reversed(concept_data):
            if entry.get("form") in ("10-K", "20-F") and entry.get("end", "").startswith(date[:4]):
                return float(entry.get("val", 0))
        return None
    except Exception:
        return None
