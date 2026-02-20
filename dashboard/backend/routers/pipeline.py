"""Pipeline endpoints — overview stats and run triggering."""

from fastapi import APIRouter, HTTPException

from models import PipelineRunRequest
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
