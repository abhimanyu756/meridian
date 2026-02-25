"""
GDELT News Ingester
Uses GDELT (Global Database of Events, Language, and Tone) - completely free, no API key.
GDELT monitors news in 65 languages across the entire world.
Docs: https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
"""
import httpx
import hashlib
from datetime import datetime, timezone
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def _simple_sentiment(text: str) -> tuple[float, str]:
    """
    Simple rule-based sentiment for demo purposes.
    In production, use Claude or a dedicated sentiment model.
    """
    NEGATIVE_WORDS = {
        "fraud", "scandal", "lawsuit", "investigation", "bankrupt", "crisis",
        "violation", "fine", "penalty", "arrested", "convicted", "collapse",
        "failure", "loss", "decline", "warning", "risk", "concern", "alleged",
    }
    POSITIVE_WORDS = {
        "growth", "profit", "award", "expansion", "innovation", "partnership",
        "record", "milestone", "success", "acquisition", "investment", "launch",
    }

    text_lower = text.lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    total = neg + pos or 1

    score = (pos - neg) / total
    label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
    return round(score, 3), label


async def ingest_company_news(company_name: str, entity_id: str, max_articles: int = 50):
    """Fetch and ingest news for a company from GDELT."""
    es = get_es_client()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            GDELT_API,
            params={
                "query": f'"{company_name}"',
                "mode": "artlist",
                "maxrecords": max_articles,
                "format": "json",
                "sort": "DateDesc",
            },
        )

        if resp.status_code != 200:
            print(f"  GDELT returned {resp.status_code} for {company_name}")
            return

        data = resp.json()
        articles = data.get("articles", [])

        for article in articles:
            title = article.get("title", "")
            url = article.get("url", "")
            seendate = article.get("seendate", "")
            domain = article.get("domain", "")

            # Parse GDELT date format: YYYYMMDDTHHMMSSZ
            try:
                pub_date = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                pub_date = datetime.now(timezone.utc)

            sentiment_score, sentiment_label = _simple_sentiment(title)

            article_id = hashlib.md5(url.encode()).hexdigest()

            doc = {
                "article_id": article_id,
                "entity_ids": [entity_id],
                "entity_names": [company_name],
                "title": title,
                "content": title,  # GDELT free tier only gives title
                "source_name": domain,
                "source_url": url,
                "published_at": pub_date.isoformat(),
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "language": article.get("language", "English"),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            await es.index(
                index=settings.index_news,
                id=article_id,
                document=doc,
            )

    print(f"  Ingested {len(articles)} news articles for {company_name} from GDELT")
