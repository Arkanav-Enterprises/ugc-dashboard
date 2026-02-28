"""Analytics endpoints — PostHog funnel/trend data + AI Q&A + snapshots."""

import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from models import AnalyticsAskRequest, SaveSnapshotRequest
from services.posthog_client import (
    get_funnel,
    get_trend,
    get_combined_summary,
    format_metrics_for_ai,
    DEFAULT_FUNNELS,
    FEATURE_EVENTS,
    RETENTION_EVENTS,
)
from services.funnel_snapshots import list_snapshots, save_snapshot

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/funnel")
async def funnel_endpoint(
    app: str = Query("manifest-lock"),
    steps: str | None = Query(None, description="Comma-separated event names"),
    date_from: str = Query("-30d"),
):
    step_list = steps.split(",") if steps else None
    return await get_funnel(app, step_list, date_from)


@router.get("/trends")
async def trends_endpoint(
    app: str = Query("manifest-lock"),
    events: str | None = Query(None, description="Comma-separated event names"),
    date_from: str = Query("-30d"),
    interval: str = Query("day"),
):
    event_list = events.split(",") if events else None
    return await get_trend(app, event_list, date_from, interval)


@router.get("/summary")
async def summary_endpoint():
    return await get_combined_summary()


@router.get("/snapshots")
async def list_snapshots_endpoint(app: str = Query("manifest-lock")):
    return list_snapshots(app)


@router.post("/snapshots")
async def save_snapshot_endpoint(req: SaveSnapshotRequest):
    funnel = await get_funnel(req.app, date_from=req.date_from)
    if funnel.get("error"):
        return {"error": funnel["error"]}
    return save_snapshot(req.app, funnel, req.notes)


@router.post("/ask")
async def ask_endpoint(req: AnalyticsAskRequest):
    """SSE streaming Claude with analytics context."""
    import anthropic
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    if not ANTHROPIC_API_KEY:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'ANTHROPIC_API_KEY not configured'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    metrics_text = await format_metrics_for_ai()

    system = f"""You are an analytics assistant for the OpenClaw project. You help analyze PostHog funnel and trend data for ManifestLock and JournalLock apps.

{metrics_text}

Answer questions about this data concisely. Reference specific numbers. Suggest actionable improvements when relevant."""

    messages = list(req.history)
    messages.append({"role": "user", "content": req.message})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async def event_generator():
        try:
            with client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
