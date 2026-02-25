"""
Reusable Elasticsearch query builders for Meridian agents.
Uses ES|QL, hybrid search, vector search, and geo queries.
"""
from config import get_settings

settings = get_settings()


def hybrid_entity_search(query: str, size: int = 10) -> dict:
    """Hybrid BM25 + vector search for entity lookup."""
    return {
        "query": {
            "bool": {
                "should": [
                    {"match": {"name": {"query": query, "boost": 2.0}}},
                    {"match": {"aliases": {"query": query}}},
                    {"fuzzy": {"name.keyword": {"value": query, "fuzziness": "AUTO"}}},
                ],
                "minimum_should_match": 1,
            }
        },
        "size": size,
    }


def esql_sentiment_trend(entity_name: str, days: int = 365) -> str:
    """ES|QL: sentiment trend over time for an entity."""
    return f"""
    FROM {settings.index_news}
    | WHERE entity_names LIKE "*{entity_name}*"
    | WHERE published_at >= NOW() - {days} days
    | EVAL month = DATE_TRUNC(1 month, published_at)
    | STATS
        avg_sentiment = AVG(sentiment_score),
        article_count = COUNT(*),
        negative_count = SUM(CASE(sentiment_label == "negative", 1, 0)),
        positive_count = SUM(CASE(sentiment_label == "positive", 1, 0))
      BY month
    | SORT month ASC
    """


def esql_legal_exposure(entity_name: str) -> str:
    """ES|QL: aggregate legal exposure for an entity."""
    return f"""
    FROM {settings.index_legal}
    | WHERE entity_names LIKE "*{entity_name}*"
    | STATS
        total_cases = COUNT(*),
        active_cases = SUM(CASE(status == "active", 1, 0)),
        total_penalties = SUM(penalty_amount),
        total_settlements = SUM(settlement_amount),
        regulatory_actions = SUM(CASE(case_type == "regulatory", 1, 0)),
        criminal_cases = SUM(CASE(case_type == "criminal", 1, 0)),
        sanctions = SUM(CASE(is_sanction == true, 1, 0))
      BY entity_names
    """


def esql_financial_trend(entity_name: str) -> str:
    """ES|QL: revenue and debt trend over time."""
    return f"""
    FROM {settings.index_filings}
    | WHERE entity_name LIKE "*{entity_name}*"
    | WHERE filing_type IN ("10-K", "annual")
    | SORT filing_date ASC
    | KEEP filing_date, revenue, net_income, total_assets, total_debt,
           auditor_opinion, going_concern, restatement
    """


def esql_executive_risk_pattern(person_id: str) -> str:
    """ES|QL: count of failed companies an executive has been associated with."""
    return f"""
    FROM {settings.index_executives}
    | WHERE person_id == "{person_id}"
    | MV_EXPAND employment_history
    | STATS
        total_roles = COUNT(*),
        failed_companies = SUM(CASE(employment_history.outcome == "company_failed", 1, 0)),
        fired_count = SUM(CASE(employment_history.outcome == "fired", 1, 0)),
        avg_tenure_days = AVG(
          DATE_DIFF("day",
            employment_history.start_date,
            COALESCE(employment_history.end_date, NOW())
          )
        )
    """


def esql_geo_risk(entity_id: str) -> str:
    """ES|QL: jurisdictions breakdown for an entity tree."""
    return f"""
    FROM {settings.index_entities}
    | WHERE entity_id == "{entity_id}" OR parent_entity_id == "{entity_id}"
    | STATS entity_count = COUNT(*) BY country_code, jurisdiction
    | SORT entity_count DESC
    """


def esql_news_volume_spike(entity_name: str, days: int = 30) -> str:
    """ES|QL: detect recent news volume spike vs historical baseline."""
    return f"""
    FROM {settings.index_news}
    | WHERE entity_names LIKE "*{entity_name}*"
    | EVAL is_recent = published_at >= NOW() - {days} days
    | STATS
        recent_count = SUM(CASE(is_recent == true, 1, 0)),
        historical_count = SUM(CASE(is_recent == false, 1, 0)),
        recent_negative = SUM(CASE(is_recent == true AND sentiment_label == "negative", 1, 0)),
        historical_negative = SUM(CASE(is_recent == false AND sentiment_label == "negative", 1, 0))
    """


def esql_auditor_changes(entity_name: str) -> str:
    """ES|QL: detect auditor changes over time (a major red flag)."""
    return f"""
    FROM {settings.index_filings}
    | WHERE entity_name LIKE "*{entity_name}*"
    | SORT filing_date ASC
    | STATS auditor_list = VALUES(auditor) BY filing_type
    """
