"""
Manifest Lock UGC Reaction Video Generator
Uses Replicate for AI avatar + MoviePy for compositing.
Assumes Replicate and MoviePy are already configured on the VPS.
"""

import os
import json
import subprocess
import requests
import replicate
from pathlib import Path
from datetime import datetime
from moviepy.editor import (
    VideoFileClip, CompositeVideoClip, TextClip,
    concatenate_videoclips, ImageClip
)
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"]
WORK_DIR = Path(os.environ.get("WORK_DIR", "/root/openclaw/output"))
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", "/root/openclaw/assets"))
WORK_DIR.mkdir(exist_ok=True)

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920


def generate_tts_audio(script: str) -> Path:
    """Generate speech audio from text using OpenAI TTS."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set — needed for TTS")

    audio_path = WORK_DIR / "tts_audio.wav"
    resp = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "tts-1", "input": script, "voice": "nova", "response_format": "wav"},
        timeout=60,
    )
    resp.raise_for_status()
    audio_path.write_bytes(resp.content)
    return audio_path


def generate_avatar_video(script: str, duration: int = 30) -> Path:
    """Generate AI talking head video via Replicate SadTalker."""
    # Replicate SadTalker requires a pre-generated audio file
    audio_path = generate_tts_audio(script)

    output = replicate.run(
        "cjwbw/sadtalker",
        input={
            "source_image": open(ASSETS_DIR / "avatar-source.png", "rb"),
            "driven_audio": open(audio_path, "rb"),
            "preprocess": "full",
            "still": True,
        },
    )
    video_url = output.url if hasattr(output, "url") else str(output)
    output_path = WORK_DIR / "avatar_raw.mp4"
    video_data = requests.get(video_url).content
    output_path.write_bytes(video_data)
    return output_path


def composite_ugc_video(
    avatar_path: Path,
    screen_recording_path: Path | None = None,
    splash_path: Path | None = None,
) -> Path:
    """
    Composite avatar with optional screen recording overlay.
    Layout: avatar fills top 60%, screen recording in bottom-right.
    """
    avatar = VideoFileClip(str(avatar_path))

    # Scale avatar to fill width, position at top
    avatar_scaled = avatar.resize(width=OUTPUT_WIDTH)

    clips = [avatar_scaled.set_position(("center", "top"))]

    if screen_recording_path and screen_recording_path.exists():
        screen = VideoFileClip(str(screen_recording_path))
        # Scale screen recording to 40% of width
        screen_w = int(OUTPUT_WIDTH * 0.4)
        screen_scaled = screen.resize(width=screen_w)
        # Position bottom-right with padding
        screen_x = OUTPUT_WIDTH - screen_w - 40
        screen_y = int(OUTPUT_HEIGHT * 0.55)
        clips.append(screen_scaled.set_position((screen_x, screen_y)))

    # Composite
    final = CompositeVideoClip(
        clips,
        size=(OUTPUT_WIDTH, OUTPUT_HEIGHT),
    ).set_duration(avatar.duration)

    # Add splash at end if provided
    if splash_path and splash_path.exists():
        splash = VideoFileClip(str(splash_path))
        splash_scaled = splash.resize(width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT)
        final = concatenate_videoclips([final, splash_scaled])

    output_path = WORK_DIR / f"ugc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    final.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
    )
    return output_path


def generate_ugc_video(
    script: str,
    screen_recording: str | None = None,
) -> Path:
    """Full pipeline: script → avatar → composite → final video."""
    print("Generating avatar video...")
    avatar_path = generate_avatar_video(script)

    screen_path = Path(screen_recording) if screen_recording else None
    splash_path = ASSETS_DIR / "splash.mp4"

    print("Compositing final video...")
    final_path = composite_ugc_video(avatar_path, screen_path, splash_path)

    print(f"Done: {final_path}")
    return final_path


if __name__ == "__main__":
    script = (
        "I found this app that literally blocks your phone until you read "
        "your manifestations out loud. I know it sounds crazy, but after "
        "using it for 2 weeks, my screen time dropped by 3 hours a day. "
        "It's called Manifest Lock, link in bio."
    )
    result = generate_ugc_video(script)
    print(f"Generated: {result}")
