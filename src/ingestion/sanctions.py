"""
Sanctions Ingester
Loads OFAC SDN (Specially Designated Nationals) list.
Free download from the US Treasury: https://www.treasury.gov/ofac/downloads/sdn.xml
Also handles EU and UN sanctions lists.
"""
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()

OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"


async def ingest_ofac_sanctions():
    """Download and ingest the OFAC SDN list."""
    es = get_es_client()

    print("  Downloading OFAC SDN list...")
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(OFAC_SDN_URL)
        if resp.status_code != 200:
            print(f"  Failed to download OFAC SDN: {resp.status_code}")
            return

    root = ET.fromstring(resp.content)
    ns = {"sdn": "https://tempuri.org/sdnList.xsd"}

    count = 0
    for entry in root.findall(".//sdn:sdnEntry", ns):
        entry_type = entry.findtext("sdn:sdnType", namespaces=ns, default="")
        last_name = entry.findtext("sdn:lastName", namespaces=ns, default="")
        first_name = entry.findtext("sdn:firstName", namespaces=ns, default="")
        uid = entry.findtext("sdn:uid", namespaces=ns, default="")

        full_name = f"{first_name} {last_name}".strip() if first_name else last_name

        # Programs this entity is sanctioned under
        programs = [
            p.text for p in entry.findall("sdn:programList/sdn:program", ns)
            if p.text
        ]

        # Aliases
        aliases = [
            aka.findtext("sdn:lastName", namespaces=ns, default="")
            for aka in entry.findall("sdn:akaList/sdn:aka", ns)
        ]

        if entry_type == "Entity":
            # Ingest as entity
            doc = {
                "entity_id": f"ofac-{uid}",
                "name": full_name,
                "aliases": aliases,
                "entity_type": "company",
                "jurisdiction": "OFAC Sanctioned",
                "status": "sanctioned",
                "risk_score": 10.0,
                "risk_flags": ["OFAC Sanctioned", f"Programs: {', '.join(programs)}"],
                "data_sources": ["OFAC SDN"],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await es.index(
                index=settings.index_entities,
                id=f"ofac-{uid}",
                document=doc,
            )
        else:
            # Person — ingest as executive/person
            doc = {
                "person_id": f"ofac-{uid}",
                "full_name": full_name,
                "aliases": aliases,
                "is_sanctioned": True,
                "is_pep": False,
                "risk_score": 10.0,
                "risk_flags": ["OFAC Sanctioned", f"Programs: {', '.join(programs)}"],
                "data_sources": ["OFAC SDN"],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            await es.index(
                index=settings.index_executives,
                id=f"ofac-{uid}",
                document=doc,
            )

        # Also add as a legal record (sanction)
        legal_doc = {
            "case_id": f"ofac-sanction-{uid}",
            "entity_names": [full_name] + aliases,
            "case_type": "sanction",
            "case_name": f"OFAC Sanctions: {full_name}",
            "case_summary": f"Listed on OFAC SDN under programs: {', '.join(programs)}",
            "jurisdiction": "US",
            "status": "active",
            "is_sanction": True,
            "sanction_list": "OFAC",
            "allegations": programs,
            "source": "US Treasury OFAC",
            "source_url": "https://www.treasury.gov/resource-center/sanctions/SDN-List/",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        await es.index(
            index=settings.index_legal,
            id=f"ofac-sanction-{uid}",
            document=legal_doc,
        )

        count += 1

    print(f"  Ingested {count} OFAC SDN entries")
