"""Project paths and environment configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is two levels up from dashboard/backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

LOGS_DIR = PROJECT_ROOT / "logs"
SKILLS_DIR = PROJECT_ROOT / "skills"
MEMORY_DIR = PROJECT_ROOT / "memory"
ASSETS_DIR = PROJECT_ROOT / "assets"
VIDEO_OUTPUT_DIR = PROJECT_ROOT / "video_output"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REF_IMAGES_DIR = ASSETS_DIR / "reference-images"

JSONL_PATH = LOGS_DIR / "video_autopilot.jsonl"
DAILY_SPEND_PATH = LOGS_DIR / "daily_spend.json"

PROJECT_VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
DAILY_COST_CAP = float(os.environ.get("DAILY_COST_CAP", "5.00"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

PERSONAS = ["sanya", "sophie", "aliyah"]
PERSONA_COLORS = {
    "sanya": "#ef4444",   # warm red
    "sophie": "#3b82f6",  # blue
    "aliyah": "#8b5cf6",  # purple
}
