#!/usr/bin/env python3
"""
Load demo data into Elasticsearch for the Meridian hackathon demo.
Creates a realistic but fictional company (Nexus Global Holdings) with
entities, executives, legal cases, and news articles.

This gives you a compelling demo without needing real API data.
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.elasticsearch.client import get_es_client, close_es_client
from src.elasticsearch.indices import create_all_indices
from config import get_settings

settings = get_settings()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample")


async def load_json_file(es, index: str, filepath: str, id_field: str):
    """Load a JSON file into an Elasticsearch index."""
    with open(filepath) as f:
        records = json.load(f)

    for record in records:
        doc_id = record.get(id_field)
        await es.index(index=index, id=doc_id, document=record)

    print(f"  Loaded {len(records)} records into {index}")
    return len(records)


async def main():
    print("Loading Meridian demo data...")
    print("=" * 50)

    es = get_es_client()

    try:
        await es.info()
    except Exception as e:
        print(f"Failed to connect to Elasticsearch: {e}")
        sys.exit(1)

    # Ensure indices exist
    await create_all_indices(es)

    # Load demo data
    total = 0
    total += await load_json_file(
        es, settings.index_entities,
        os.path.join(DATA_DIR, "companies.json"),
        "entity_id"
    )
    total += await load_json_file(
        es, settings.index_executives,
        os.path.join(DATA_DIR, "executives.json"),
        "person_id"
    )
    total += await load_json_file(
        es, settings.index_legal,
        os.path.join(DATA_DIR, "legal_cases.json"),
        "case_id"
    )
    total += await load_json_file(
        es, settings.index_news,
        os.path.join(DATA_DIR, "news.json"),
        "article_id"
    )

    print("=" * 50)
    print(f"Demo data loaded: {total} total records")
    print()
    print("Now try investigating: 'Nexus Global Holdings'")
    print("  curl -X POST http://localhost:8000/investigate \\")
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"target": "Nexus Global Holdings"}\'')

    await close_es_client()


if __name__ == "__main__":
    asyncio.run(main())
