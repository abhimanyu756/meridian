from elasticsearch import AsyncElasticsearch
from functools import lru_cache
from config import get_settings

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        settings = get_settings()
        if settings.es_api_key:
            _client = AsyncElasticsearch(
                settings.es_url,
                api_key=settings.es_api_key,
            )
        else:
            _client = AsyncElasticsearch(
                settings.es_url,
                basic_auth=(settings.es_username, settings.es_password),
                verify_certs=False,
            )
    return _client


async def close_es_client():
    global _client
    if _client:
        await _client.close()
        _client = None
