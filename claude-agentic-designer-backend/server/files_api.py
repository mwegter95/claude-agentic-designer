"""Reference library API: persistent master deck + examples with on/off toggles.

Files can be local uploads or SharePoint/OneDrive share URLs (Microsoft 365). The
library persists across runs; each entry can be toggled "referenced" or not for a run.
"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.paths import references_dir  # noqa: E402

from .graph_client import graph  # noqa: E402
from .models import (  # noqa: E402
    AddSharePointRequest,
    ReferenceFile,
    ToggleRequest,
    UpdateReferenceRequest,
)
from .storage import load_library, save_library  # noqa: E402

router = APIRouter(prefix="/api/references", tags=["references"])


def _files() -> List[ReferenceFile]:
    return [ReferenceFile(**f) for f in load_library().get("files", [])]


def _persist(files: List[ReferenceFile]) -> None:
    save_library({"files": [f.model_dump() for f in files]})


@router.get("")
def list_references() -> dict:
    return {"files": [f.model_dump() for f in _files()]}


@router.get("/enabled")
def enabled_references() -> dict:
    """What the skill should reference for a run: enabled entries with usable paths."""
    out = []
    for f in _files():
        if not f.enabled:
            continue
        local = f.cached_path or (str(references_dir() / f.path) if f.path else None)
        out.append({
            "id": f.id,
            "name": f.name,
            "role": f.role,
            "source": f.source,
            "url": f.url,
            "local_path": local,
            "available": bool(local and Path(local).exists()),
        })
    return {"files": out}


@router.post("/upload")
async def upload_reference(
    file: UploadFile = File(...),
    role: str = Form("example"),
) -> dict:
    rid = uuid.uuid4().hex[:12]
    safe_name = Path(file.filename or "upload.bin").name
    rel = f"{rid}__{safe_name}"
    dest = references_dir() / rel
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    entry = ReferenceFile(
        id=rid,
        name=safe_name,
        source="upload",
        role=role,
        enabled=True,
        path=rel,
        size=dest.stat().st_size,
        content_type=file.content_type,
        cached_path=str(dest),
    )
    files = _files()
    files.append(entry)
    _persist(files)
    return entry.model_dump()


@router.post("/sharepoint")
def add_sharepoint(req: AddSharePointRequest) -> dict:
    rid = uuid.uuid4().hex[:12]
    name = req.name or req.url.split("/")[-1].split("?")[0] or "sharepoint-file"
    entry = ReferenceFile(
        id=rid, name=name, source="sharepoint", role=req.role,
        enabled=True, url=req.url,
    )
    files = _files()
    files.append(entry)
    _persist(files)
    return entry.model_dump()


@router.post("/{rid}/download")
def download_sharepoint(rid: str) -> dict:
    files = _files()
    entry = next((f for f in files if f.id == rid), None)
    if not entry:
        raise HTTPException(404, "Reference not found")
    if entry.source != "sharepoint" or not entry.url:
        raise HTTPException(400, "Not a SharePoint reference")
    if not graph.configured:
        raise HTTPException(400, "Microsoft 365 not configured (GRAPH_CLIENT_ID).")
    if not graph.signed_in:
        raise HTTPException(401, "Not signed in to Microsoft 365.")
    dest = references_dir() / f"{entry.id}__{entry.name}"
    try:
        graph.download_share(entry.url, dest)
    except Exception as exc:
        raise HTTPException(502, f"Graph download failed: {exc}")
    entry.cached_path = str(dest)
    entry.size = dest.stat().st_size
    _persist(files)
    return entry.model_dump()


@router.patch("/{rid}/toggle")
def toggle_reference(rid: str, req: ToggleRequest) -> dict:
    files = _files()
    entry = next((f for f in files if f.id == rid), None)
    if not entry:
        raise HTTPException(404, "Reference not found")
    entry.enabled = req.enabled
    _persist(files)
    return entry.model_dump()


@router.patch("/{rid}")
def update_reference(rid: str, req: UpdateReferenceRequest) -> dict:
    files = _files()
    entry = next((f for f in files if f.id == rid), None)
    if not entry:
        raise HTTPException(404, "Reference not found")
    if req.role is not None:
        entry.role = req.role
    if req.name is not None:
        entry.name = req.name
    _persist(files)
    return entry.model_dump()


@router.delete("/{rid}")
def delete_reference(rid: str) -> dict:
    files = _files()
    entry = next((f for f in files if f.id == rid), None)
    if not entry:
        raise HTTPException(404, "Reference not found")
    if entry.cached_path:
        try:
            Path(entry.cached_path).unlink(missing_ok=True)
        except Exception:
            pass
    files = [f for f in files if f.id != rid]
    _persist(files)
    return {"ok": True}
