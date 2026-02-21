"""Schedule endpoints — view and edit cron schedule config."""

from fastapi import APIRouter

from models import ScheduleUpdateRequest
from services.schedule_reader import get_schedule, update_schedule

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("")
def read_schedule():
    """Return full schedule state: config, slots, last runs, cron history."""
    return get_schedule()


@router.put("")
def write_schedule(req: ScheduleUpdateRequest):
    """Update schedule config (enable/disable personas, video type override)."""
    return update_schedule(req.model_dump(exclude_none=True))
