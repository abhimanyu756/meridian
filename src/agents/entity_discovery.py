"""
Agent 1: Entity Discovery
Finds a company and maps its full corporate ownership structure.
Discovers subsidiaries, parent companies, shell companies, and related entities.
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from src.elasticsearch.queries import hybrid_entity_search
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MERIDIAN's Entity Discovery Agent. Your role is to analyze corporate ownership
structure data and identify risks in how a company is organized.

Analyze the provided corporate data and assess:
1. Complexity of corporate structure (many layers = higher risk)
2. Presence of shell companies or holding companies in opaque jurisdictions
3. Unusual ownership patterns (circular ownership, multiple nominees)
4. Related party relationships that could indicate conflicts of interest

Respond with a JSON object:
{
  "findings": "Clear 2-3 paragraph narrative of what you found",
  "risk_score": <float 0.0-10.0>,
  "red_flags": ["flag1", "flag2", ...]
}
"""


class EntityDiscoveryAgent(BaseAgent):
    def __init__(self):
        super().__init__("Entity Discovery")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            # Step 1: Find the primary entity
            primary_results = await self._search(
                settings.index_entities,
                hybrid_entity_search(target, size=5),
            )

            if not primary_results:
                finding.complete(
                    findings=f"No corporate registration records found for '{target}' in our database.",
                    risk_score=2.0,
                    red_flags=["No corporate records found"],
                )
                return finding

            primary = primary_results[0]
            entity_id = primary.get("entity_id", "")

            # Step 2: Find subsidiaries
            subsidiaries = await self._search(
                settings.index_entities,
                {
                    "query": {"term": {"parent_entity_id": entity_id}},
                    "size": 50,
                },
            )

            # Step 3: Count jurisdictions and flag high-risk ones
            HIGH_RISK_JURISDICTIONS = {
                "BVI", "Cayman Islands", "Panama", "Marshall Islands",
                "Seychelles", "Belize", "Vanuatu", "Mauritius", "Samoa",
            }

            all_entities = [primary] + subsidiaries
            jurisdictions = [e.get("jurisdiction", "") for e in all_entities]
            high_risk_jurs = [j for j in jurisdictions if j in HIGH_RISK_JURISDICTIONS]

            corporate_data = {
                "primary_entity": {
                    "name": primary.get("name"),
                    "jurisdiction": primary.get("jurisdiction"),
                    "incorporation_date": primary.get("incorporation_date"),
                    "status": primary.get("status"),
                    "entity_type": primary.get("entity_type"),
                },
                "total_subsidiaries": len(subsidiaries),
                "all_jurisdictions": list(set(jurisdictions)),
                "high_risk_jurisdictions": list(set(high_risk_jurs)),
                "subsidiary_sample": [
                    {
                        "name": s.get("name"),
                        "jurisdiction": s.get("jurisdiction"),
                        "status": s.get("status"),
                    }
                    for s in subsidiaries[:10]
                ],
            }

            # Step 4: Claude analyzes the structure
            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Analyze this corporate structure for '{target}':\n\n{json.dumps(corporate_data, indent=2)}",
            )

            result = json.loads(response)
            finding.raw_data = corporate_data
            finding.complete(
                findings=result["findings"],
                risk_score=result["risk_score"],
                red_flags=result["red_flags"],
            )

        except Exception as e:
            finding.fail(str(e))

        return finding
