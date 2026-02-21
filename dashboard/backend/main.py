"""OpenClaw Dashboard — FastAPI backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import logs, pipeline, content, knowledge, assets, chat, schedule, youtube_research

app = FastAPI(title="OpenClaw Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router)
app.include_router(pipeline.router)
app.include_router(content.router)
app.include_router(knowledge.router)
app.include_router(assets.router)
app.include_router(chat.router)
app.include_router(schedule.router)
app.include_router(youtube_research.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
