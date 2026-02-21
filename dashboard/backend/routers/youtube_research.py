"""YouTube research endpoints — channel scanning and analysis."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import YTChannelScanRequest, YTAnalyzeRequest
from services.youtube_research import scan_channel, run_analysis, list_research, load_research

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/scan")
def scan(req: YTChannelScanRequest):
    """Scan a YouTube channel and return video list."""
    try:
        return scan_channel(req.channel_url, req.max_videos)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="yt-dlp not installed")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze(req: YTAnalyzeRequest):
    """SSE streaming analysis of selected videos."""
    async def event_generator():
        try:
            async for event in run_analysis(
                req.channel_name, req.channel_url, req.video_ids, req.video_titles
            ):
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
def get_results():
    """List all saved research results."""
    return list_research()


@router.get("/results/{research_id}")
def get_result(research_id: str):
    """Get a specific saved research result."""
    result = load_research(research_id)
    if not result:
        raise HTTPException(status_code=404, detail="Research not found")
    return result
