"""Reddit research endpoints — search and analysis."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import RedditSearchRequest, RedditAnalyzeRequest
from services.reddit_research import search_reddit, run_reddit_analysis

router = APIRouter(prefix="/api/research/reddit", tags=["research"])


@router.post("/search")
def search(req: RedditSearchRequest):
    """Search Reddit for threads matching query."""
    try:
        return search_reddit(req.query, req.subreddits, req.time_filter, req.limit)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze(req: RedditAnalyzeRequest):
    """SSE streaming analysis of selected Reddit threads."""
    async def event_generator():
        try:
            async for event in run_reddit_analysis(req.query, req.threads):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
