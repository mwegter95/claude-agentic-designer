"""Microsoft 365 auth + runs/artifacts API."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.paths import run_dir, run_renders_dir  # noqa: E402

from .events_hub import hub  # noqa: E402
from .graph_client import graph  # noqa: E402
from .storage import load_runs  # noqa: E402

router = APIRouter(prefix="/api", tags=["runs"])


# ── Microsoft 365 auth ────────────────────────────────────────────────────────
@router.get("/m365/status")
def m365_status() -> dict:
    return {"configured": graph.configured, "signed_in": graph.signed_in}


@router.post("/m365/login/begin")
def m365_login_begin() -> dict:
    try:
        return graph.begin_device_login()
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/m365/login/complete")
def m365_login_complete() -> dict:
    try:
        ok = graph.complete_device_login()
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {"signed_in": ok}


# ── runs ──────────────────────────────────────────────────────────────────────
@router.get("/runs")
def list_runs() -> dict:
    runs = load_runs().get("runs", {})
    ordered = sorted(runs.values(), key=lambda r: r.get("created_at", 0), reverse=True)
    return {"runs": ordered}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    runs = load_runs().get("runs", {})
    if run_id not in runs:
        raise HTTPException(404, "Run not found")
    return {"run": runs[run_id], "events": hub.buffer(run_id)}


@router.get("/runs/{run_id}/events")
def get_run_events(run_id: str) -> dict:
    return {"events": hub.buffer(run_id)}


@router.get("/runs/{run_id}/renders/{name}")
def get_render(run_id: str, name: str):
    path = run_renders_dir(run_id) / Path(name).name
    if not path.exists():
        raise HTTPException(404, "Render not found")
    return FileResponse(str(path))


@router.get("/runs/{run_id}/artifact")
def get_artifact(run_id: str):
    runs = load_runs().get("runs", {})
    run = runs.get(run_id)
    if not run or not run.get("artifact"):
        raise HTTPException(404, "Artifact not found")
    path = Path(run["artifact"])
    if not path.exists():
        # fall back to conventional location
        path = run_dir(run_id) / "output.pptx"
    if not path.exists():
        raise HTTPException(404, "Artifact file missing")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=path.name,
    )
