"""
Agent 4: Executive Background Agent
Profiles key executives/directors, traces their history across companies,
detects PEP status, prior failures, conflicts of interest.
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MERIDIAN's Executive Background Agent. You analyze the backgrounds
of executives and directors to identify risk patterns.

Key risk signals:
1. Executives previously at companies that went bankrupt or were involved in fraud
2. Politically Exposed Persons (PEPs) - government officials, their families/associates
3. Sanctioned individuals
4. Short tenures at multiple companies (serial failure pattern)
5. Board interlocks with conflicted or risky entities
6. Executives from high-risk jurisdictions
7. Multiple companies connected to the same group of insiders

Respond with a JSON object:
{
  "findings": "Clear 2-3 paragraph narrative on executive risk profiles",
  "risk_score": <float 0.0-10.0>,
  "red_flags": ["flag1", "flag2", ...]
}
"""


class ExecutiveBackgroundAgent(BaseAgent):
    def __init__(self):
        super().__init__("Executive Background")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            entity_id = context.get("entity_id", "")

            # Step 1: Find executives linked to this entity
            executives = await self._search(
                settings.index_executives,
                {
                    "query": {
                        "bool": {
                            "should": [
                                {"term": {"current_entity_id": entity_id}},
                                {"match": {"employment_history.entity_name": target}},
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                    "size": 20,
                },
            )

            # Step 2: Flag high-risk executives
            peps = [e for e in executives if e.get("is_pep")]
            sanctioned = [e for e in executives if e.get("is_sanctioned")]
            high_risk = [e for e in executives if (e.get("risk_score") or 0) >= 7.0]

            exec_data = {
                "company": target,
                "executives_found": len(executives),
                "pep_count": len(peps),
                "sanctioned_count": len(sanctioned),
                "high_risk_count": len(high_risk),
                "executive_profiles": [
                    {
                        "name": e.get("full_name"),
                        "title": e.get("current_title"),
                        "is_pep": e.get("is_pep"),
                        "is_sanctioned": e.get("is_sanctioned"),
                        "risk_score": e.get("risk_score"),
                        "risk_flags": e.get("risk_flags", []),
                        "nationalities": e.get("nationalities", []),
                        "employment_history": e.get("employment_history", [])[:5],
                        "pep_details": e.get("pep_details"),
                    }
                    for e in executives[:10]
                ],
            }

            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Analyze executive backgrounds for '{target}':\n\n{json.dumps(exec_data, indent=2)}",
            )

            result = json.loads(response)
            finding.raw_data = exec_data
            finding.complete(
                findings=result["findings"],
                risk_score=result["risk_score"],
                red_flags=result["red_flags"],
            )

        except Exception as e:
            finding.fail(str(e))

        return finding
