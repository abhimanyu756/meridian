"""
Vector / Semantic search utilities for Meridian.
Uses Gemini embedding API to generate vectors, then Elasticsearch kNN search.
Showcases dense_vector + cosine similarity capabilities.
"""
import asyncio
from google import genai
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()
_gemini = genai.Client(api_key=settings.anthropic_api_key)


async def get_embedding(text: str) -> list[float]:
    """Generate a 384-dim embedding using Gemini's embedding model."""
    result = await asyncio.to_thread(
        _gemini.models.embed_content,
        model="gemini-embedding-001",
        contents=text,
        config=genai.types.EmbedContentConfig(output_dimensionality=384),
    )
    return result.embeddings[0].values


async def semantic_search_news(query: str, size: int = 5) -> list[dict]:
    """
    Semantic search over news articles using kNN vector search.
    1. Embed the query text
    2. Run kNN search on content_vector field
    3. Return ranked results with scores
    """
    es = get_es_client()
    vector = await get_embedding(query)

    result = await es.search(
        index=settings.index_news,
        knn={
            "field": "content_vector",
            "query_vector": vector,
            "k": size,
            "num_candidates": 50,
        },
        source=["title", "entity_names", "source_name", "published_at",
                "sentiment_label", "sentiment_score", "topics"],
    )

    hits = []
    for hit in result["hits"]["hits"]:
        doc = hit["_source"]
        doc["_score"] = hit["_score"]
        hits.append(doc)
    return hits


async def embed_and_update_news():
    """
    Batch-embed all news articles that lack a content_vector.
    Used during data ingestion to populate vectors for kNN search.
    """
    es = get_es_client()

    # Find docs without vectors
    result = await es.search(
        index=settings.index_news,
        body={
            "query": {
                "bool": {
                    "must_not": {"exists": {"field": "content_vector"}}
                }
            },
            "size": 100,
            "_source": ["title", "content", "article_id"],
        },
    )

    docs = result["hits"]["hits"]
    if not docs:
        return 0

    count = 0
    for doc in docs:
        src = doc["_source"]
        text = (src.get("title", "") + " " + src.get("content", ""))[:500]
        if not text.strip():
            continue

        try:
            vector = await get_embedding(text)
            await es.update(
                index=settings.index_news,
                id=doc["_id"],
                body={"doc": {"content_vector": vector}},
            )
            count += 1
            # Rate limit: small delay between embedding calls
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"  Failed to embed {doc['_id']}: {e}")

    return count
