"""Subprocess management for pipeline runs."""

import queue
import subprocess
import threading
import uuid
from datetime import datetime, timezone

from config import PROJECT_ROOT, PROJECT_VENV_PYTHON, SCRIPTS_DIR
from models import PipelineRunRequest, PipelineRunStatus, LifestyleReelRequest, AutoJournalReelRequest

# In-memory store for run tracking
_runs: dict[str, dict] = {}

# Sequential queue — runs execute one at a time to avoid overloading the VPS
_queue: queue.Queue[tuple[str, list[str]]] = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _ensure_worker():
    """Start the background worker thread (once)."""
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
        thread = threading.Thread(target=_worker_loop, daemon=True)
        thread.start()


def _worker_loop():
    """Process queued runs one at a time."""
    while True:
        run_id, cmd = _queue.get()
        try:
            _runs[run_id]["status"] = "running"
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
        finally:
            _queue.task_done()


def start_pipeline_run(req: PipelineRunRequest) -> PipelineRunStatus:
    """Queue a pipeline run for sequential execution."""
    run_id = str(uuid.uuid4())[:8]

    cmd = [str(PROJECT_VENV_PYTHON), str(SCRIPTS_DIR / "autopilot.py"),
           "--account", req.account]

    if req.dry_run:
        cmd.append("--dry-run")
    if req.no_upload:
        cmd.append("--no-upload")
    if req.no_reaction:
        cmd.append("--no-reaction")
    if req.idea_only:
        cmd.append("--idea-only")
    if req.hook_text:
        cmd += ["--hook-text", req.hook_text]
    if req.reaction_text:
        cmd += ["--reaction-text", req.reaction_text]

    # Derive persona from account name for display
    persona = req.account.split(".")[0] if "." in req.account else req.account

    _runs[run_id] = {
        "id": run_id,
        "status": "queued",
        "persona": persona,
        "app": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "output": "",
        "process": None,
    }

    _ensure_worker()
    _queue.put((run_id, cmd))

    return PipelineRunStatus(
        id=run_id,
        status="queued",
        persona=persona,
        app=None,
        started_at=_runs[run_id]["started_at"],
    )


def start_lifestyle_run(req: LifestyleReelRequest) -> PipelineRunStatus:
    """Queue a lifestyle reel pipeline run for sequential execution."""
    run_id = str(uuid.uuid4())[:8]

    cmd = [str(PROJECT_VENV_PYTHON), str(SCRIPTS_DIR / "lifestyle_reel.py")]

    if req.dry_run:
        cmd.append("--dry-run")
    if req.no_upload:
        cmd.append("--no-upload")
    if req.scene_1_text:
        cmd += ["--scene-1-text", req.scene_1_text]
    if req.scene_2_text:
        cmd += ["--scene-2-text", req.scene_2_text]
    if req.scene_3_text:
        cmd += ["--scene-3-text", req.scene_3_text]
    if req.scene_1_image:
        cmd += ["--scene-1-image", req.scene_1_image]
    if req.scene_2_image:
        cmd += ["--scene-2-image", req.scene_2_image]

    _runs[run_id] = {
        "id": run_id,
        "status": "queued",
        "persona": "lifestyle",
        "app": "journal-lock",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "output": "",
        "process": None,
    }

    _ensure_worker()
    _queue.put((run_id, cmd))

    return PipelineRunStatus(
        id=run_id,
        status="queued",
        persona="lifestyle",
        app="journal-lock",
        started_at=_runs[run_id]["started_at"],
    )


def start_autojournal_run(req: AutoJournalReelRequest) -> PipelineRunStatus:
    """Queue an AutoJournal reel pipeline run for sequential execution."""
    run_id = str(uuid.uuid4())[:8]

    cmd = [str(PROJECT_VENV_PYTHON), str(SCRIPTS_DIR / "autojournal_reel.py")]

    if req.dry_run:
        cmd.append("--dry-run")
    if req.no_upload:
        cmd.append("--no-upload")
    if req.style:
        cmd += ["--style", req.style]
    if req.category:
        cmd += ["--category", req.category]
    if req.hook_text:
        cmd += ["--hook-text", req.hook_text]
    if req.payoff_text:
        cmd += ["--payoff-text", req.payoff_text]

    _runs[run_id] = {
        "id": run_id,
        "status": "queued",
        "persona": "autojournal",
        "app": "autojournal",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "output": "",
        "process": None,
    }

    _ensure_worker()
    _queue.put((run_id, cmd))

    return PipelineRunStatus(
        id=run_id,
        status="queued",
        persona="autojournal",
        app="autojournal",
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
        app=run.get("app"),
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
            app=r.get("app"),
            started_at=r["started_at"],
            output=r["output"][-500:] if r["output"] else "",
        )
        for r in _runs.values()
    ]
