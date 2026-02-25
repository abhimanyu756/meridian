"""
Agent 7: Risk Synthesis Agent (Master Reasoning Agent)
Collects all findings from the 6 specialist agents and synthesizes them
into a final risk score, executive summary, and recommended actions.
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MERIDIAN's Risk Synthesis Agent — the final reasoning layer.
You receive findings from 6 specialized intelligence agents and synthesize them into
a comprehensive, actionable risk assessment.

Your synthesis must:
1. Calculate a WEIGHTED final risk score (legal/financial issues weigh more than geo/narrative)
2. Identify cross-agent patterns (e.g., offshore structure + weak financials + legal issues = fraud pattern)
3. Assess the COMBINATION of risks (1+1 > 2 in risk assessment)
4. Provide a clear executive summary a CFO/CCO/board member would act on
5. Give specific, prioritized recommended actions

Risk level thresholds:
- 0-2.5: LOW - Standard due diligence sufficient
- 2.5-5.0: MEDIUM - Enhanced due diligence recommended
- 5.0-7.5: HIGH - Material concerns, escalate to senior management
- 7.5-10.0: CRITICAL - Do not proceed without full forensic investigation

Respond with a JSON object:
{
  "overall_risk_score": <float 0.0-10.0>,
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "executive_summary": "3-5 paragraph executive summary",
  "top_red_flags": ["most critical flag 1", "flag 2", "flag 3"],
  "cross_agent_patterns": ["pattern 1", "pattern 2"],
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "proceed_recommendation": "APPROVE|CONDITIONAL|REJECT|INVESTIGATE_FURTHER"
}
"""

# Weights for each agent's risk score in the final calculation
AGENT_WEIGHTS = {
    "Legal Intelligence": 0.30,
    "Financial Signal": 0.25,
    "Executive Background": 0.20,
    "Entity Discovery": 0.10,
    "Sentiment & Narrative": 0.08,
    "Geo & Jurisdiction": 0.07,
}


class RiskSynthesisAgent(BaseAgent):
    def __init__(self):
        super().__init__("Risk Synthesis")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            agent_findings = context.get("agent_findings", [])

            # Step 1: Build weighted risk score
            weighted_score = 0.0
            all_red_flags = []
            findings_summary = {}

            for af in agent_findings:
                agent_name = af.get("agent_name", "")
                weight = AGENT_WEIGHTS.get(agent_name, 0.05)
                risk = af.get("risk_contribution", 0.0)
                weighted_score += risk * weight
                all_red_flags.extend(af.get("red_flags", []))
                findings_summary[agent_name] = {
                    "risk_score": risk,
                    "weight": weight,
                    "weighted_contribution": risk * weight,
                    "key_findings": af.get("findings", "")[:500],
                    "red_flags": af.get("red_flags", []),
                }

            synthesis_input = {
                "company": target,
                "preliminary_weighted_score": round(weighted_score, 2),
                "total_red_flags": len(all_red_flags),
                "unique_red_flags": list(set(all_red_flags)),
                "agent_findings_summary": findings_summary,
            }

            # Step 2: Claude synthesizes all findings
            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Synthesize all investigation findings for '{target}':\n\n{json.dumps(synthesis_input, indent=2)}",
            )

            result = json.loads(response)

            # Step 3: Store the final investigation in Elasticsearch
            investigation_doc = {
                "target_name": target,
                "overall_risk_score": result["overall_risk_score"],
                "risk_level": result["risk_level"],
                "summary": result["executive_summary"],
                "red_flags": result["top_red_flags"],
                "recommended_actions": "\n".join(result["recommended_actions"]),
                "agent_findings": [af for af in agent_findings],
                "status": "complete",
            }

            finding.raw_data = {
                "synthesis": result,
                "input_summary": synthesis_input,
            }

            finding.complete(
                findings=result["executive_summary"],
                risk_score=result["overall_risk_score"],
                red_flags=result["top_red_flags"],
            )

            # Attach full result to finding for the orchestrator
            finding.full_result = result

        except Exception as e:
            finding.fail(str(e))

        return finding
