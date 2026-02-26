"""
Agent 5: Sentiment & Narrative Agent
Time-series sentiment analysis across news sources.
Detects narrative shifts, coordinated PR campaigns, and emerging controversies.
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from src.elasticsearch.queries import (
    esql_sentiment_trend,
    esql_news_volume_spike,
)
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MERIDIAN's Sentiment & Narrative Agent. You analyze news coverage
and public sentiment trends to detect reputational risks and narrative manipulation.

Identify:
1. Sudden sentiment shifts (positive → negative) - often precede major revelations
2. News volume spikes - high volume of negative news = active crisis
3. Sustained negative coverage over years - entrenched reputational damage
4. Discrepancy between official narrative and press coverage (PR vs reality)
5. Coordinated positive coverage followed by controversy (astroturfing pattern)
6. Coverage concentrated in specific geographies (geo-specific risk)

Respond with a JSON object:
{
  "findings": "Clear 2-3 paragraph narrative of the public sentiment picture",
  "risk_score": <float 0.0-10.0>,
  "red_flags": ["flag1", "flag2", ...]
}
"""


class SentimentAgent(BaseAgent):
    def __init__(self):
        super().__init__("Sentiment & Narrative")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            # Step 1: Sentiment trend over time (ES|QL time-series)
            trend_1yr = await self._run_esql(esql_sentiment_trend(target, days=365))
            trend_5yr = await self._run_esql(esql_sentiment_trend(target, days=1825))

            # Step 2: Detect recent volume spikes
            spike_data = await self._run_esql(esql_news_volume_spike(target, days=30))

            # Step 3: Get recent negative articles for narrative context
            negative_news = await self._search(
                settings.index_news,
                {
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"entity_names": target}},
                                {"term": {"sentiment_label": "negative"}},
                            ]
                        }
                    },
                    "sort": [{"published_at": {"order": "desc"}}],
                    "size": 10,
                },
            )

            # Step 4: Get recent positive articles too for balance
            positive_news = await self._search(
                settings.index_news,
                {
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"entity_names": target}},
                                {"term": {"sentiment_label": "positive"}},
                            ]
                        }
                    },
                    "sort": [{"published_at": {"order": "desc"}}],
                    "size": 5,
                },
            )

            sentiment_data = {
                "company": target,
                "sentiment_trend_1yr": trend_1yr if trend_1yr else "No trend data available",
                "sentiment_trend_5yr": trend_5yr[:12] if trend_5yr else "No long-term trend data",
                "volume_spike_analysis": spike_data if spike_data else "No spike data available",
                "total_negative_articles": len(negative_news),
                "total_positive_articles": len(positive_news),
                "recent_negative_articles": [
                    {
                        "title": a.get("title"),
                        "source": a.get("source_name"),
                        "date": a.get("published_at"),
                        "sentiment": a.get("sentiment_score"),
                        "topics": a.get("topics", []),
                    }
                    for a in negative_news
                ],
                "recent_positive_articles": [
                    {
                        "title": a.get("title"),
                        "source": a.get("source_name"),
                        "date": a.get("published_at"),
                    }
                    for a in positive_news
                ],
            }

            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Analyze sentiment and narrative for '{target}':\n\n{json.dumps(sentiment_data, indent=2)}",
            )

            result = json.loads(response)
            finding.raw_data = sentiment_data
            finding.complete(
                findings=result["findings"],
                risk_score=result["risk_score"],
                red_flags=result["red_flags"],
            )

        except Exception as e:
            finding.fail(str(e))

        return finding
