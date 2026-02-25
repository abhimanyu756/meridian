"""
Meridian FastAPI application.
Provides REST + Server-Sent Events (SSE) endpoints for real-time investigation streaming.
"""
import uuid
import json
import asyncio
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agents.orchestrator import investigate
from src.elasticsearch.client import get_es_client, close_es_client
from src.elasticsearch.indices import create_all_indices
from config import get_settings

settings = get_settings()

app = FastAPI(
    title="MERIDIAN",
    description="Multi-Agent Corporate Intelligence & Due Diligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


@app.on_event("startup")
async def startup():
    es = get_es_client()
    await create_all_indices(es)


@app.on_event("shutdown")
async def shutdown():
    await close_es_client()


# ---------- Models ----------

class InvestigateRequest(BaseModel):
    target: str
    investigation_id: str | None = None


# ---------- Routes ----------

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/investigate/stream")
async def investigate_stream(req: InvestigateRequest):
    """
    Start an investigation and stream real-time events via Server-Sent Events.
    Each event is a JSON object pushed as `data: {...}\\n\\n`.
    """
    investigation_id = req.investigation_id or str(uuid.uuid4())

    async def event_generator():
        async for event in investigate(req.target, investigation_id):
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0)  # yield control to allow streaming
        yield "data: {\"event\": \"stream_end\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/investigate")
async def investigate_sync(req: InvestigateRequest):
    """
    Start an investigation and wait for full completion (non-streaming).
    Returns the complete report as JSON.
    """
    investigation_id = req.investigation_id or str(uuid.uuid4())
    final_event = None

    async for event in investigate(req.target, investigation_id):
        if event.get("event") == "investigation_complete":
            final_event = event

    if not final_event:
        raise HTTPException(status_code=500, detail="Investigation failed to complete")

    return JSONResponse(content=final_event)


@app.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str):
    """Retrieve a past investigation by ID."""
    es = get_es_client()
    try:
        result = await es.get(
            index=settings.index_investigations,
            id=investigation_id,
        )
        return JSONResponse(content=result["_source"])
    except Exception:
        raise HTTPException(status_code=404, detail="Investigation not found")


@app.get("/investigations")
async def list_investigations(size: int = 20):
    """List recent investigations."""
    es = get_es_client()
    result = await es.search(
        index=settings.index_investigations,
        body={
            "query": {"match_all": {}},
            "sort": [{"started_at": {"order": "desc"}}],
            "size": size,
        },
    )
    hits = [h["_source"] for h in result["hits"]["hits"]]
    return JSONResponse(content={"investigations": hits, "total": result["hits"]["total"]["value"]})


@app.get("/search/entities")
async def search_entities(q: str, size: int = 10):
    """Search for entities by name."""
    es = get_es_client()
    result = await es.search(
        index=settings.index_entities,
        body={
            "query": {
                "bool": {
                    "should": [
                        {"match": {"name": {"query": q, "boost": 2.0}}},
                        {"match": {"aliases": q}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": size,
        },
    )
    return JSONResponse(content={"entities": [h["_source"] for h in result["hits"]["hits"]]})


@app.post("/esql")
async def run_esql(body: dict):
    """
    Execute an ES|QL query directly (for Kibana dashboard integration).
    Body: { "query": "FROM meridian-news | ..." }
    """
    es = get_es_client()
    try:
        result = await es.esql.query(body=body)
        return JSONResponse(content=result.body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
