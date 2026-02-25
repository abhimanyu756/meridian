"""
Meridian Orchestrator
Coordinates all 7 agents, runs specialist agents in parallel,
then feeds findings to the Risk Synthesis Agent.
Streams real-time progress updates via async generator.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from src.agents.base import AgentFinding
from src.agents.entity_discovery import EntityDiscoveryAgent
from src.agents.financial_signal import FinancialSignalAgent
from src.agents.legal_intelligence import LegalIntelligenceAgent
from src.agents.executive_background import ExecutiveBackgroundAgent
from src.agents.sentiment import SentimentAgent
from src.agents.geo_jurisdiction import GeoJurisdictionAgent
from src.agents.risk_synthesis import RiskSynthesisAgent
from src.elasticsearch.client import get_es_client
from config import get_settings

settings = get_settings()


def _risk_level(score: float) -> str:
    if score < 2.5:
        return "LOW"
    elif score < 5.0:
        return "MEDIUM"
    elif score < 7.5:
        return "HIGH"
    return "CRITICAL"


async def investigate(
    target: str,
    investigation_id: str,
) -> AsyncGenerator[dict, None]:
    """
    Main orchestration function.
    Yields status events as the investigation progresses.
    Each event is a dict that can be serialized to JSON for SSE/WebSocket streaming.
    """
    es = get_es_client()

    # --- Phase 0: Initialize investigation record ---
    await es.index(
        index=settings.index_investigations,
        id=investigation_id,
        document={
            "investigation_id": investigation_id,
            "target_name": target,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "agent_findings": [],
        },
    )

    yield {
        "event": "investigation_started",
        "investigation_id": investigation_id,
        "target": target,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # --- Phase 1: Entity Discovery (must run first to get entity_id for other agents) ---
    yield {"event": "agent_started", "agent": "Entity Discovery"}

    entity_agent = EntityDiscoveryAgent()
    entity_finding = await entity_agent.run(target, {})
    entity_id = entity_finding.raw_data.get("primary_entity", {}).get("entity_id", "")

    yield {
        "event": "agent_complete",
        "agent": "Entity Discovery",
        "risk_score": entity_finding.risk_contribution,
        "red_flags": entity_finding.red_flags,
        "findings": entity_finding.findings,
    }

    shared_context = {"entity_id": entity_id}

    # --- Phase 2: Run 5 specialist agents in staggered batches ---
    #     (Gemini free tier = 5 req/min, so stagger to avoid rate limits)
    batch_1 = [
        FinancialSignalAgent(),
        LegalIntelligenceAgent(),
        ExecutiveBackgroundAgent(),
    ]
    batch_2 = [
        SentimentAgent(),
        GeoJurisdictionAgent(),
    ]

    for agent in batch_1 + batch_2:
        yield {"event": "agent_started", "agent": agent.name}

    # Batch 1: run 3 agents
    tasks_1 = [agent.run(target, shared_context) for agent in batch_1]
    findings_1: list[AgentFinding] = await asyncio.gather(*tasks_1)

    for finding in findings_1:
        yield {
            "event": "agent_complete",
            "agent": finding.agent_name,
            "risk_score": finding.risk_contribution,
            "red_flags": finding.red_flags,
            "findings": finding.findings,
        }

    # Brief pause between batches to respect rate limits
    await asyncio.sleep(2)

    # Batch 2: run remaining 2 agents
    tasks_2 = [agent.run(target, shared_context) for agent in batch_2]
    findings_2: list[AgentFinding] = await asyncio.gather(*tasks_2)

    for finding in findings_2:
        yield {
            "event": "agent_complete",
            "agent": finding.agent_name,
            "risk_score": finding.risk_contribution,
            "red_flags": finding.red_flags,
            "findings": finding.findings,
        }

    specialist_findings = list(findings_1) + list(findings_2)

    # --- Phase 3: Risk Synthesis (final agent) ---
    yield {"event": "agent_started", "agent": "Risk Synthesis"}

    all_findings = [entity_finding] + list(specialist_findings)
    synthesis_context = {
        "agent_findings": [f.to_dict() for f in all_findings],
    }

    synthesis_agent = RiskSynthesisAgent()
    synthesis_finding = await synthesis_agent.run(target, synthesis_context)

    full_result = getattr(synthesis_finding, "full_result", {})

    yield {
        "event": "agent_complete",
        "agent": "Risk Synthesis",
        "risk_score": synthesis_finding.risk_contribution,
        "red_flags": synthesis_finding.red_flags,
        "findings": synthesis_finding.findings,
    }

    # --- Phase 4: Save final report to Elasticsearch ---
    final_doc = {
        "investigation_id": investigation_id,
        "target_name": target,
        "target_entity_id": entity_id,
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "overall_risk_score": synthesis_finding.risk_contribution,
        "risk_level": _risk_level(synthesis_finding.risk_contribution),
        "agent_findings": [f.to_dict() for f in all_findings + [synthesis_finding]],
        "summary": synthesis_finding.findings,
        "red_flags": synthesis_finding.red_flags,
        "recommended_actions": json.dumps(full_result.get("recommended_actions", [])),
    }

    await es.index(
        index=settings.index_investigations,
        id=investigation_id,
        document=final_doc,
    )

    # --- Phase 5: Yield final report ---
    yield {
        "event": "investigation_complete",
        "investigation_id": investigation_id,
        "target": target,
        "overall_risk_score": synthesis_finding.risk_contribution,
        "risk_level": _risk_level(synthesis_finding.risk_contribution),
        "executive_summary": synthesis_finding.findings,
        "top_red_flags": synthesis_finding.red_flags,
        "recommended_actions": full_result.get("recommended_actions", []),
        "proceed_recommendation": full_result.get("proceed_recommendation", "INVESTIGATE_FURTHER"),
        "agent_findings": [f.to_dict() for f in all_findings],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
