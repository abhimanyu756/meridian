"""
Agent 3: Legal Intelligence Agent
Searches court records, regulatory actions, and sanctions lists.
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from src.elasticsearch.queries import esql_legal_exposure
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MERIDIAN's Legal Intelligence Agent. You analyze legal records, regulatory
actions, and sanctions to assess legal risk.

Assess:
1. Criminal cases (highest risk) vs civil disputes (moderate risk)
2. Regulatory actions from major regulators (SEC, DOJ, FTC, FDA)
3. Sanctions list appearances (OFAC, EU, UN) - CRITICAL risk
4. Settlement amounts and penalties (financial scale of wrongdoing)
5. Ongoing vs resolved cases (ongoing = active risk)
6. Patterns of repeated violations across multiple jurisdictions

Respond with a JSON object:
{
  "findings": "Clear 2-3 paragraph narrative of legal exposure",
  "risk_score": <float 0.0-10.0>,
  "red_flags": ["flag1", "flag2", ...]
}
"""


class LegalIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__("Legal Intelligence")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            # Step 1: Aggregate legal exposure via ES|QL
            exposure_rows = await self._run_esql(esql_legal_exposure(target))

            # Step 2: Get individual cases for narrative detail
            cases = await self._search(
                settings.index_legal,
                {
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"entity_names": target}},
                                {"match": {"case_name": target}},
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                    "sort": [{"filed_date": {"order": "desc"}}],
                    "size": 20,
                },
            )

            # Step 3: Check sanctions specifically
            sanctions = [c for c in cases if c.get("is_sanction")]
            criminal = [c for c in cases if c.get("case_type") == "criminal"]
            regulatory = [c for c in cases if c.get("case_type") == "regulatory"]

            legal_data = {
                "company": target,
                "total_cases": len(cases),
                "sanctions": len(sanctions),
                "criminal_cases": len(criminal),
                "regulatory_actions": len(regulatory),
                "aggregated_exposure": exposure_rows,
                "notable_cases": [
                    {
                        "name": c.get("case_name"),
                        "type": c.get("case_type"),
                        "filed": c.get("filed_date"),
                        "status": c.get("status"),
                        "outcome": c.get("outcome"),
                        "penalty": c.get("penalty_amount"),
                        "settlement": c.get("settlement_amount"),
                        "allegations": c.get("allegations", []),
                        "regulator": c.get("regulator"),
                        "is_sanction": c.get("is_sanction"),
                        "sanction_list": c.get("sanction_list"),
                    }
                    for c in cases[:10]
                ],
            }

            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Analyze legal exposure for '{target}':\n\n{json.dumps(legal_data, indent=2)}",
            )

            result = json.loads(response)
            finding.raw_data = legal_data
            finding.complete(
                findings=result["findings"],
                risk_score=result["risk_score"],
                red_flags=result["red_flags"],
            )

        except Exception as e:
            finding.fail(str(e))

        return finding
