"""
Agent 2: Financial Signal Agent
Analyzes SEC filings and financial data for red flags:
- Auditor changes, going concern warnings, restatements
- Revenue/debt trends, deteriorating financials
- Unusual related-party transactions
"""
import json
from src.agents.base import BaseAgent, AgentFinding
from src.elasticsearch.queries import esql_financial_trend, esql_auditor_changes
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MERIDIAN's Financial Signal Agent. You analyze financial filings to detect
warning signs of financial distress, fraud, or mismanagement.

Key red flags to identify:
- Going concern warnings from auditors
- Auditor changes (especially to smaller, less-known firms)
- Financial restatements
- Rapidly increasing debt relative to revenue
- Declining margins over multiple periods
- Unexplained revenue spikes or drops
- Qualified or adverse audit opinions

Respond with a JSON object:
{
  "findings": "Clear 2-3 paragraph narrative of financial health and risks",
  "risk_score": <float 0.0-10.0>,
  "red_flags": ["flag1", "flag2", ...]
}
"""


class FinancialSignalAgent(BaseAgent):
    def __init__(self):
        super().__init__("Financial Signal")

    async def run(self, target: str, context: dict) -> AgentFinding:
        finding = AgentFinding(self.name)
        try:
            # Step 1: Pull financial trend via ES|QL
            trend_rows = await self._run_esql(esql_financial_trend(target))
            auditor_rows = await self._run_esql(esql_auditor_changes(target))

            # Step 2: Pull latest filings directly
            filings = await self._search(
                settings.index_filings,
                {
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"entity_name": target}},
                            ]
                        }
                    },
                    "sort": [{"filing_date": {"order": "desc"}}],
                    "size": 10,
                },
            )

            # Step 3: Compute quick metrics
            going_concern_count = sum(1 for f in filings if f.get("going_concern"))
            restatement_count = sum(1 for f in filings if f.get("restatement"))
            qualified_opinions = [
                f for f in filings
                if f.get("auditor_opinion") not in ("clean", None)
            ]

            financial_data = {
                "company": target,
                "filings_analyzed": len(filings),
                "going_concern_warnings": going_concern_count,
                "restatements": restatement_count,
                "non_clean_audit_opinions": len(qualified_opinions),
                "financial_trend": trend_rows[:8] if trend_rows else "No financial trend data available",
                "auditor_history": auditor_rows if auditor_rows else "No auditor history available",
                "recent_filings": [
                    {
                        "date": f.get("filing_date"),
                        "type": f.get("filing_type"),
                        "revenue": f.get("revenue"),
                        "net_income": f.get("net_income"),
                        "total_debt": f.get("total_debt"),
                        "auditor": f.get("auditor"),
                        "opinion": f.get("auditor_opinion"),
                        "going_concern": f.get("going_concern"),
                        "restatement": f.get("restatement"),
                    }
                    for f in filings[:5]
                ],
            }

            response = await self._ask_llm(
                SYSTEM_PROMPT,
                f"Analyze the financial data for '{target}':\n\n{json.dumps(financial_data, indent=2)}",
            )

            result = json.loads(response)
            finding.raw_data = financial_data
            finding.complete(
                findings=result["findings"],
                risk_score=result["risk_score"],
                red_flags=result["red_flags"],
            )

        except Exception as e:
            finding.fail(str(e))

        return finding
