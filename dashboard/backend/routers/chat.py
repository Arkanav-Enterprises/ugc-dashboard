"""Chat endpoints — SSE streaming + WebSocket fallback."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.claude_chat import stream_chat
from services.skill_loader import list_skill_files, list_memory_files

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    skill_files: list[str] | None = None
    memory_files: list[str] | None = None


@router.get("/context-files")
def get_context_files():
    """List available skill and memory files for context selection."""
    return {
        "skills": list_skill_files(),
        "memory": list_memory_files(),
    }


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """SSE endpoint for streaming Claude chat (works through Vercel proxy)."""
    messages = list(req.history)
    messages.append({"role": "user", "content": req.message})

    async def event_generator():
        try:
            async for chunk in stream_chat(messages, req.skill_files, req.memory_files):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.websocket("/ws")
async def chat_websocket(ws: WebSocket):
    """WebSocket endpoint for local development."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)

            user_message = payload.get("message", "")
            history = payload.get("history", [])
            skill_files = payload.get("skill_files")
            memory_files = payload.get("memory_files")

            messages = list(history)
            messages.append({"role": "user", "content": user_message})

            try:
                async for chunk in stream_chat(messages, skill_files, memory_files):
                    await ws.send_text(json.dumps({"type": "chunk", "content": chunk}))
                await ws.send_text(json.dumps({"type": "done"}))
            except Exception as e:
                await ws.send_text(json.dumps({"type": "error", "content": str(e)}))

    except WebSocketDisconnect:
        pass
