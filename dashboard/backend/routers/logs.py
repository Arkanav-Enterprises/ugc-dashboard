"""Log endpoints — runs and spend data."""

from fastapi import APIRouter

from services.log_reader import read_all_runs, get_daily_spend_list

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/runs")
def get_runs():
    """Get all pipeline runs from JSONL."""
    return read_all_runs()


@router.get("/spend")
def get_spend():
    """Get daily spend data."""
    return get_daily_spend_list()
