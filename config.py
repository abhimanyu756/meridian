from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Elasticsearch
    es_url: str = "http://localhost:9200"
    es_api_key: str = ""
    es_username: str = "elastic"
    es_password: str = "changeme"

    # Gemini
    anthropic_api_key: str = ""  # Kept for backward compat, now used as Gemini key

    # Optional data sources
    news_api_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # Elasticsearch index names
    index_entities: str = "meridian-entities"
    index_filings: str = "meridian-filings"
    index_legal: str = "meridian-legal"
    index_news: str = "meridian-news"
    index_executives: str = "meridian-executives"
    index_investigations: str = "meridian-investigations"

    # Gemini model
    gemini_model: str = "gemini-2.5-flash"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
