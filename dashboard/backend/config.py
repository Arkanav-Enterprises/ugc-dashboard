"""Project paths and environment configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Pipeline root — override with PIPELINE_ROOT env var, otherwise
# assume the pipeline lives two levels up (works for local dev where
# the dashboard lives inside the openclaw project).
PROJECT_ROOT = Path(os.environ.get("PIPELINE_ROOT", Path(__file__).resolve().parent.parent.parent))
load_dotenv(PROJECT_ROOT / ".env", override=True)

LOGS_DIR = PROJECT_ROOT / "logs"
SKILLS_DIR = PROJECT_ROOT / "skills"
MEMORY_DIR = PROJECT_ROOT / "memory"
ASSETS_DIR = PROJECT_ROOT / "assets"
VIDEO_OUTPUT_DIR = PROJECT_ROOT / "video_output"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REF_IMAGES_DIR = ASSETS_DIR / "reference-images"

SCHEDULE_CONFIG = PROJECT_ROOT / "config" / "schedule.json"
JSONL_PATH = LOGS_DIR / "video_autopilot.jsonl"
DAILY_SPEND_PATH = LOGS_DIR / "daily_spend.json"

import shutil

_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"
PROJECT_VENV_PYTHON = _venv_python if _venv_python.exists() else Path(shutil.which("python3") or "python3")
DAILY_COST_CAP = float(os.environ.get("DAILY_COST_CAP", "5.00"))


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

PERSONAS = ["sanya", "sophie", "aliyah"]
PERSONA_COLORS = {
    "sanya": "#ef4444",   # warm red
    "sophie": "#3b82f6",  # blue
    "aliyah": "#8b5cf6",  # purple
}
