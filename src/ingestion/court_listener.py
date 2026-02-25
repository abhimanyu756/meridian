"""
CourtListener Ingester
Uses the free CourtListener API for US federal court records.
API docs: https://www.courtlistener.com/api/rest/v3/
No API key required for basic access.
"""
import httpx
from datetime import datetime, timezone
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()

COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"


async def ingest_company_cases(company_name: str, entity_id: str):
    """Search CourtListener for cases involving a company and ingest them."""
    es = get_es_client()

    async with httpx.AsyncClient(timeout=30) as client:
        # Search dockets (court cases)
        resp = await client.get(
            f"{COURTLISTENER_BASE}/dockets/",
            params={
                "q": company_name,
                "order_by": "date_filed desc",
                "page_size": 20,
            },
            headers={"Accept": "application/json"},
        )

        if resp.status_code != 200:
            print(f"  CourtListener returned {resp.status_code} for {company_name}")
            return

        data = resp.json()
        results = data.get("results", [])

        for case in results:
            case_number = case.get("docket_number", "")
            case_name = case.get("case_name", "")
            court = case.get("court_id", "")
            date_filed = case.get("date_filed")
            date_terminated = case.get("date_terminated")
            nature_of_suit = case.get("nature_of_suit", "")

            # Determine case type from nature of suit
            case_type = "civil"
            if any(w in nature_of_suit.lower() for w in ["securities", "fraud", "antitrust"]):
                case_type = "regulatory"

            status = "resolved" if date_terminated else "active"

            doc = {
                "case_id": f"cl-{case_number.replace(' ', '-')}",
                "entity_ids": [entity_id],
                "entity_names": [company_name],
                "case_type": case_type,
                "case_name": case_name,
                "case_summary": f"{nature_of_suit} - {case_name}",
                "court": court,
                "jurisdiction": "US Federal",
                "filed_date": date_filed,
                "resolved_date": date_terminated,
                "status": status,
                "allegations": [nature_of_suit] if nature_of_suit else [],
                "is_sanction": False,
                "source": "CourtListener",
                "source_url": f"https://www.courtlistener.com{case.get('absolute_url', '')}",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            await es.index(
                index=settings.index_legal,
                id=doc["case_id"],
                document=doc,
            )

    print(f"  Ingested {len(results)} court cases for {company_name} from CourtListener")
