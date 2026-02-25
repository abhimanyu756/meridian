#!/usr/bin/env python3
"""
Ingest real public data into Meridian from free sources:
  - SEC EDGAR (no API key needed)
  - GDELT News (no API key needed)
  - CourtListener (no API key needed)
  - OFAC Sanctions List (no API key needed)

Usage:
  python scripts/ingest_real_data.py --company "Tesla" --cik 1318605
  python scripts/ingest_real_data.py --sanctions  # load full OFAC list
"""
import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.elasticsearch.client import get_es_client, close_es_client
from src.elasticsearch.indices import create_all_indices
from src.ingestion.sec_edgar import ingest_company as ingest_sec
from src.ingestion.gdelt_news import ingest_company_news
from src.ingestion.court_listener import ingest_company_cases
from src.ingestion.sanctions import ingest_ofac_sanctions


async def main():
    parser = argparse.ArgumentParser(description="Ingest real data into Meridian")
    parser.add_argument("--company", help="Company name to ingest")
    parser.add_argument("--cik", help="SEC CIK number for the company")
    parser.add_argument("--entity-id", help="Entity ID to use", default=None)
    parser.add_argument("--sanctions", action="store_true", help="Load OFAC sanctions list")
    parser.add_argument("--all-sources", action="store_true", help="Ingest from all available sources")
    args = parser.parse_args()

    es = get_es_client()
    try:
        await es.info()
    except Exception as e:
        print(f"Failed to connect to Elasticsearch: {e}")
        sys.exit(1)

    await create_all_indices(es)

    if args.sanctions:
        print("Loading OFAC sanctions list (this may take a few minutes)...")
        await ingest_ofac_sanctions()

    if args.company:
        entity_id = args.entity_id or f"manual-{args.company.lower().replace(' ', '-')}"
        print(f"\nIngesting data for: {args.company}")

        if args.cik:
            print("  SEC EDGAR...")
            await ingest_sec(args.company, args.cik)

        print("  GDELT News...")
        await ingest_company_news(args.company, entity_id)

        print("  CourtListener...")
        await ingest_company_cases(args.company, entity_id)

    await close_es_client()
    print("\nIngestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
