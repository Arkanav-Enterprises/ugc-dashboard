"""Mass outreach endpoints — parse markdown, send batch via SSE, history."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import OutreachParseRequest, OutreachSendRequest
from services.email_sender import (
    list_accounts,
    parse_outreach_markdown,
    send_batch,
    list_batch_results,
    load_batch_result,
)

router = APIRouter(prefix="/api/outreach", tags=["outreach"])


@router.get("/accounts")
def accounts():
    """List sender accounts (passwords redacted)."""
    return list_accounts()


@router.post("/parse")
def parse(req: OutreachParseRequest):
    """Parse outreach markdown into structured email list."""
    emails = parse_outreach_markdown(req.markdown)
    return {"emails": emails}


@router.post("/send")
async def send(req: OutreachSendRequest):
    """SSE streaming batch send."""
    async def event_generator():
        try:
            emails = [e.model_dump() for e in req.emails]
            async for event in send_batch(
                emails,
                req.account_label,
                req.delay_seconds,
                req.from_name,
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


@router.get("/history")
def history():
    """List past outreach batches."""
    return list_batch_results()


@router.get("/history/{batch_id}")
def history_detail(batch_id: str):
    """Get a specific outreach batch result."""
    data = load_batch_result(batch_id)
    if not data:
        raise HTTPException(status_code=404, detail="Batch not found")
    return data
