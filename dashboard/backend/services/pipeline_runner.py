"""Subprocess management for pipeline runs."""

import subprocess
import threading
import uuid
from datetime import datetime, timezone

from config import PROJECT_ROOT, PROJECT_VENV_PYTHON, SCRIPTS_DIR
from models import PipelineRunRequest, PipelineRunStatus

# In-memory store for run tracking
_runs: dict[str, dict] = {}


def start_pipeline_run(req: PipelineRunRequest) -> PipelineRunStatus:
    """Start a pipeline run as a subprocess."""
    run_id = str(uuid.uuid4())[:8]

    cmd = [str(PROJECT_VENV_PYTHON), str(SCRIPTS_DIR / "autopilot_video.py"),
           "--persona", req.persona]

    if req.video_type:
        cmd += ["--video-type", req.video_type]
    if req.dry_run:
        cmd.append("--dry-run")
    if req.no_upload:
        cmd.append("--no-upload")
    if req.skip_gen:
        cmd.append("--skip-gen")

    _runs[run_id] = {
        "id": run_id,
        "status": "running",
        "persona": req.persona,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "output": "",
        "process": None,
    }

    def _run():
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=None,  # inherit env (dotenv loaded in config)
            )
            _runs[run_id]["process"] = proc
            output_lines = []
            for line in proc.stdout:
                output_lines.append(line)
                _runs[run_id]["output"] = "".join(output_lines)
            proc.wait()
            _runs[run_id]["status"] = "completed" if proc.returncode == 0 else "failed"
        except Exception as e:
            _runs[run_id]["status"] = "failed"
            _runs[run_id]["output"] += f"\nError: {e}"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return PipelineRunStatus(
        id=run_id,
        status="running",
        persona=req.persona,
        started_at=_runs[run_id]["started_at"],
    )


def get_run_status(run_id: str) -> PipelineRunStatus | None:
    """Get the current status of a run."""
    run = _runs.get(run_id)
    if not run:
        return None
    return PipelineRunStatus(
        id=run["id"],
        status=run["status"],
        persona=run["persona"],
        started_at=run["started_at"],
        output=run["output"],
    )


def list_runs() -> list[PipelineRunStatus]:
    """List all tracked runs."""
    return [
        PipelineRunStatus(
            id=r["id"],
            status=r["status"],
            persona=r["persona"],
            started_at=r["started_at"],
            output=r["output"][-500:] if r["output"] else "",
        )
        for r in _runs.values()
    ]
