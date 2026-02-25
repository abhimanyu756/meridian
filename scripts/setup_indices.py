#!/usr/bin/env python3
"""
Create all Meridian Elasticsearch indices.
Run this once before starting the application.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.elasticsearch.client import get_es_client, close_es_client
from src.elasticsearch.indices import create_all_indices


async def main():
    print("Setting up Meridian Elasticsearch indices...")
    es = get_es_client()

    try:
        # Test connection
        info = await es.info()
        print(f"Connected to Elasticsearch: {info['version']['number']}")
    except Exception as e:
        print(f"Failed to connect to Elasticsearch: {e}")
        print("Make sure Elasticsearch is running (docker-compose up -d)")
        sys.exit(1)

    await create_all_indices(es)
    print("\nAll indices created successfully!")

    await close_es_client()


if __name__ == "__main__":
    asyncio.run(main())
