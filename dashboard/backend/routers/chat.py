"""Chat endpoint — WebSocket streaming Claude."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.claude_chat import stream_chat
from services.skill_loader import list_skill_files, list_memory_files

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/context-files")
def get_context_files():
    """List available skill and memory files for context selection."""
    return {
        "skills": list_skill_files(),
        "memory": list_memory_files(),
    }


@router.websocket("/ws")
async def chat_websocket(ws: WebSocket):
    """WebSocket endpoint for streaming Claude chat.

    Client sends JSON: {"message": "...", "history": [...], "skill_files": [...], "memory_files": [...]}
    Server streams JSON: {"type": "chunk", "content": "..."} or {"type": "done"}
    """
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)

            user_message = payload.get("message", "")
            history = payload.get("history", [])
            skill_files = payload.get("skill_files")
            memory_files = payload.get("memory_files")

            # Build messages list
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
