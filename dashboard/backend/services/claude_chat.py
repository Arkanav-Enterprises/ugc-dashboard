"""Anthropic streaming chat with skill context."""

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from services.skill_loader import load_context


def build_system_prompt(skill_files: list[str] | None = None, memory_files: list[str] | None = None) -> str:
    """Build system prompt with loaded skill context."""
    context = load_context(skill_files, memory_files)
    return f"""You are the OpenClaw content engine assistant. You help create, analyze, and optimize UGC-style video content for the ManifestLock and JournalLock apps.

You have access to the following knowledge:

{context}

You can help with:
- Generating hook text and reaction text for reels
- Analyzing content performance
- Suggesting content angles and strategies
- Reviewing and improving captions
- Answering questions about the pipeline and content strategy

Be concise, creative, and speak in a Gen Z-friendly voice when generating content. For strategy questions, be analytical and data-driven."""


async def stream_chat(messages: list[dict], skill_files: list[str] | None = None, memory_files: list[str] | None = None):
    """Stream a chat response from Claude. Yields text chunks."""
    if not ANTHROPIC_API_KEY:
        yield "Error: ANTHROPIC_API_KEY not configured"
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system = build_system_prompt(skill_files, memory_files)

    with client.messages.stream(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
