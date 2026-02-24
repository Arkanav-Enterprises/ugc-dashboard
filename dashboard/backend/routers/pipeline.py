"""Pipeline endpoints — overview stats and run triggering."""

from fastapi import APIRouter, HTTPException

from config import PERSONA_APPS, PERSONA_COLORS
from models import PersonaAppInfo, PersonaConfig, PipelineRunRequest
from services.log_reader import get_overview_stats, get_persona_stats
from services.pipeline_runner import start_pipeline_run, get_run_status, list_runs

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/overview")
def overview():
    """Get overview stats (today's runs, costs, totals)."""
    return {
        "stats": get_overview_stats(),
        "personas": get_persona_stats(),
    }


@router.get("/personas")
def get_personas():
    """Return persona configs with apps and video types."""
    return [
        PersonaConfig(
            persona=name,
            color=PERSONA_COLORS.get(name, "#888"),
            apps=[PersonaAppInfo(**a) for a in cfg["apps"]],
            video_types=cfg["video_types"],
        )
        for name, cfg in PERSONA_APPS.items()
    ]


@router.post("/run")
def trigger_run(req: PipelineRunRequest):
    """Trigger a new pipeline run."""
    run = start_pipeline_run(req)
    return run


@router.get("/run/{run_id}")
def run_status(run_id: str):
    """Get status of a pipeline run."""
    status = get_run_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@router.get("/runs/active")
def active_runs():
    """List all tracked runs."""
    return list_runs()
