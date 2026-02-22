"""Opportunity Scout endpoints — expand seeds, run full scout, list/load results."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import ScoutRunRequest, ScoutExpandSeedsRequest
from services.opportunity_scout import (
    expand_seeds,
    run_scout,
    list_scout_results,
    load_scout_result,
)

router = APIRouter(prefix="/api/scout", tags=["scout"])


@router.post("/expand-seeds")
def expand(req: ScoutExpandSeedsRequest):
    """Expand seed keywords via iTunes autocomplete."""
    try:
        keywords = expand_seeds(req.seeds)
        return {"keywords": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def run(req: ScoutRunRequest):
    """SSE streaming full scout pipeline."""
    async def event_generator():
        try:
            async for event in run_scout(req.seeds, req.skip_reviews, req.skip_reddit):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/results")
def results():
    """List past scout results."""
    return list_scout_results()


@router.get("/results/{result_id}")
def result(result_id: str):
    """Get a specific scout result."""
    data = load_scout_result(result_id)
    if not data:
        raise HTTPException(status_code=404, detail="Result not found")
    return data
