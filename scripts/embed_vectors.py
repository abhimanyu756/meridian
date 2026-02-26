"""
Embed news articles with Gemini embedding API for kNN vector search.
Run this after ingest_all.py to populate content_vector fields.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from elasticsearch import AsyncElasticsearch
from config import get_settings

settings = get_settings()
gemini = genai.Client(api_key=settings.anthropic_api_key)


def get_es():
    if settings.es_api_key:
        return AsyncElasticsearch(settings.es_url, api_key=settings.es_api_key)
    return AsyncElasticsearch(
        settings.es_url,
        basic_auth=(settings.es_username, settings.es_password),
        verify_certs=False,
    )


async def get_embedding(text: str) -> list[float]:
    """Generate a 384-dim embedding using Gemini."""
    result = await asyncio.to_thread(
        gemini.models.embed_content,
        model="gemini-embedding-001",
        contents=text,
        config=genai.types.EmbedContentConfig(output_dimensionality=384),
    )
    return result.embeddings[0].values


async def embed_index(es, index: str, text_fields: list[str], vector_field: str):
    """Embed all docs in an index that lack a vector."""
    # Find docs without vectors
    result = await es.search(
        index=index,
        body={
            "query": {
                "bool": {
                    "must_not": {"exists": {"field": vector_field}}
                }
            },
            "size": 200,
            "_source": text_fields + ["article_id", "filing_id", "entity_id", "person_id"],
        },
    )

    docs = result["hits"]["hits"]
    total = len(docs)
    if total == 0:
        print(f"  {index}: All documents already have vectors")
        return 0

    print(f"  {index}: Embedding {total} documents...")
    count = 0

    for i, doc in enumerate(docs):
        src = doc["_source"]
        # Build text from available fields
        text_parts = [str(src.get(f, "")) for f in text_fields if src.get(f)]
        text = " ".join(text_parts)[:500]
        if not text.strip():
            continue

        try:
            vector = await get_embedding(text)
            await es.update(
                index=index,
                id=doc["_id"],
                body={"doc": {vector_field: vector}},
            )
            count += 1
            if (i + 1) % 10 == 0:
                print(f"    Progress: {i + 1}/{total}")
            # Rate limit
            await asyncio.sleep(0.15)
        except Exception as e:
            print(f"    Failed {doc['_id']}: {e}")
            await asyncio.sleep(1)

    return count


async def main():
    es = get_es()
    print("MERIDIAN — Vector Embedding Pipeline")
    print("=" * 50)

    # Embed news articles
    news_count = await embed_index(
        es, "meridian-news",
        text_fields=["title", "content"],
        vector_field="content_vector",
    )
    print(f"  News: {news_count} documents embedded")

    # Embed legal cases
    legal_count = await embed_index(
        es, "meridian-legal",
        text_fields=["case_name", "case_summary"],
        vector_field="summary_vector",
    )
    print(f"  Legal: {legal_count} documents embedded")

    # Embed filings
    filings_count = await embed_index(
        es, "meridian-filings",
        text_fields=["title", "content_summary"],
        vector_field="content_vector",
    )
    print(f"  Filings: {filings_count} documents embedded")

    # Embed entities
    entity_count = await embed_index(
        es, "meridian-entities",
        text_fields=["name"],
        vector_field="name_vector",
    )
    print(f"  Entities: {entity_count} documents embedded")

    # Embed executives
    exec_count = await embed_index(
        es, "meridian-executives",
        text_fields=["full_name", "bio_summary"],
        vector_field="name_vector",
    )
    print(f"  Executives: {exec_count} documents embedded")

    total = news_count + legal_count + filings_count + entity_count + exec_count
    print(f"\nTotal: {total} documents embedded across all indices")

    await es.close()


if __name__ == "__main__":
    asyncio.run(main())
