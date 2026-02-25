"""
Agent 6: Geo & Jurisdiction Agent
Maps corporate structure geographically, flags high-risk jurisdictions,
detects data sovereignty risks, and identifies offshore exposure.
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from src.elasticsearch.queries import esql_geo_risk
from config import get_settings

settings = get_settings()

# Risk tiers for jurisdictions
HIGH_RISK_JURISDICTIONS = {
    "BVI": "British Virgin Islands - Major offshore secrecy jurisdiction",
    "Cayman Islands": "Tax haven with limited transparency",
    "Panama": "High financial secrecy, historical fraud cases",
    "Marshall Islands": "Ship registry haven, low transparency",
    "Seychelles": "Popular for shell companies",
    "Belize": "Low-regulation offshore center",
    "Vanuatu": "Pacific offshore secrecy jurisdiction",
    "Mauritius": "Used for treaty shopping",
    "Samoa": "Offshore financial center",
    "Anguilla": "British offshore territory",
    "Nevis": "Strong asset protection laws",
    "Labuan": "Malaysian offshore center",
}

SANCTIONED_COUNTRIES = {
    "Iran", "North Korea", "Syria", "Cuba", "Russia", "Belarus",
    "Myanmar", "Venezuela", "Zimbabwe",
}

SYSTEM_PROMPT = """You are MERIDIAN's Geo & Jurisdiction Agent. You analyze geographic and
jurisdictional risk in a company's corporate structure and operations.

Key risk indicators:
1. Presence in high-secrecy offshore jurisdictions (BVI, Cayman, Panama, etc.)
2. Operations in OFAC-sanctioned countries
3. Complex multi-layer structures spanning many jurisdictions (layering = obfuscation)
4. Mismatch between claimed operations and jurisdictions (e.g., UK company, all subs in BVI)
5. Data flowing through jurisdictions with weak data protection laws
6. Tax haven usage inconsistent with stated business purpose

Respond with a JSON object:
{
  "findings": "Clear 2-3 paragraph narrative of geographic and jurisdictional risk",
  "risk_score": <float 0.0-10.0>,
  "red_flags": ["flag1", "flag2", ...]
}
"""


class GeoJurisdictionAgent(BaseAgent):
    def __init__(self):
        super().__init__("Geo & Jurisdiction")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            entity_id = context.get("entity_id", "")

            # Step 1: ES|QL geo breakdown of all related entities
            geo_rows = await self._run_esql(esql_geo_risk(entity_id))

            # Step 2: Get all entities for geo_point aggregation
            entities = await self._search(
                settings.index_entities,
                {
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"name": target}},
                                {"term": {"parent_entity_id": entity_id}},
                            ]
                        }
                    },
                    "aggs": {
                        "by_jurisdiction": {
                            "terms": {"field": "jurisdiction", "size": 30}
                        },
                        "geo_centroid": {
                            "geo_centroid": {"field": "geo_location"}
                        },
                    },
                    "size": 0,
                },
            )

            # Step 3: Cross-reference with risk lists
            all_jurisdictions = [row.get("jurisdiction", "") for row in geo_rows]
            high_risk_found = {
                j: HIGH_RISK_JURISDICTIONS[j]
                for j in all_jurisdictions
                if j in HIGH_RISK_JURISDICTIONS
            }
            sanctioned_found = [j for j in all_jurisdictions if j in SANCTIONED_COUNTRIES]

            geo_data = {
                "company": target,
                "jurisdiction_breakdown": geo_rows,
                "total_jurisdictions": len(set(all_jurisdictions)),
                "high_risk_jurisdictions_found": high_risk_found,
                "sanctioned_country_exposure": sanctioned_found,
                "offshore_entity_count": sum(
                    row.get("entity_count", 0)
                    for row in geo_rows
                    if row.get("jurisdiction") in HIGH_RISK_JURISDICTIONS
                ),
            }

            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Analyze geo/jurisdictional risk for '{target}':\n\n{json.dumps(geo_data, indent=2)}",
            )

            result = json.loads(response)
            finding.raw_data = geo_data
            finding.complete(
                findings=result["findings"],
                risk_score=result["risk_score"],
                red_flags=result["red_flags"],
            )

        except Exception as e:
            finding.fail(str(e))

        return finding
