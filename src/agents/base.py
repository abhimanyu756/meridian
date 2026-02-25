"""
Base agent class for all Meridian agents.
Each agent uses Gemini for reasoning + Elasticsearch for data retrieval.
"""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from google import genai
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()


class AgentFinding:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.status = "running"
        self.findings: str = ""
        self.risk_contribution: float = 0.0
        self.red_flags: list[str] = []
        self.raw_data: dict = {}
        self.completed_at: datetime | None = None

    def complete(self, findings: str, risk_score: float, red_flags: list[str]):
        self.findings = findings
        self.risk_contribution = risk_score
        self.red_flags = red_flags
        self.status = "complete"
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error: str):
        self.findings = f"Agent error: {error}"
        self.status = "error"
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "findings": self.findings,
            "risk_contribution": self.risk_contribution,
            "red_flags": self.red_flags,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BaseAgent(ABC):
    """
    Base class for all Meridian agents.
    Subclasses implement `run()` which:
      1. Queries Elasticsearch for relevant data
      2. Passes structured data to Gemini for reasoning
      3. Returns an AgentFinding
    """

    def __init__(self, name: str):
        self.name = name
        self.es = get_es_client()
        self.gemini = genai.Client(api_key=settings.anthropic_api_key)

    @abstractmethod
    async def run(self, target: str, context: dict) -> AgentFinding:
        """Execute the agent investigation."""
        ...

    async def _ask_llm(self, system_prompt: str, user_message: str) -> str:
        """Send a reasoning request to Gemini with automatic retry on rate limits."""
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.gemini.models.generate_content,
                    model=settings.gemini_model,
                    contents=user_message,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                    ),
                )
                return response.text
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = (attempt + 1) * 15  # 15s, 30s, 45s, 60s
                    print(f"  [{self.name}] Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    raise
        raise Exception(f"Gemini rate limit exceeded after {max_retries} retries")

    async def _run_esql(self, query: str) -> list[dict]:
        """Execute an ES|QL query and return rows as list of dicts."""
        try:
            result = await self.es.esql.query(body={"query": query})
            columns = [col["name"] for col in result.get("columns", [])]
            rows = result.get("values", [])
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            return [{"error": str(e)}]

    async def _search(self, index: str, body: dict) -> list[dict]:
        """Run an Elasticsearch search and return hits."""
        try:
            result = await self.es.search(index=index, body=body)
            return [hit["_source"] for hit in result["hits"]["hits"]]
        except Exception as e:
            return [{"error": str(e)}]

    async def _knn_search(self, index: str, vector: list[float], field: str, k: int = 5) -> list[dict]:
        """Run a kNN vector search."""
        try:
            result = await self.es.search(
                index=index,
                knn={"field": field, "query_vector": vector, "k": k, "num_candidates": 50},
            )
            return [hit["_source"] for hit in result["hits"]["hits"]]
        except Exception as e:
            return [{"error": str(e)}]
