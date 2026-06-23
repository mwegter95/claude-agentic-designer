"""Filesystem layout helpers shared by skill tools and the FastAPI server.

Single source of truth for where reference files, runs, and artifacts live so the
skill scripts (run by Claude) and the server (serving the UI) always agree.
"""
from __future__ import annotations

import os
from pathlib import Path


def workspace_root() -> Path:
    env = os.environ.get("CLAUDE_DESIGNER_WORKSPACE", "").strip()
    if env:
        root = Path(env).expanduser().resolve()
    else:
        # Default to <repo>/workspace
        root = Path(__file__).resolve().parents[2] / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    return root


def references_dir() -> Path:
    d = workspace_root() / "references"
    d.mkdir(parents=True, exist_ok=True)
    return d


def references_index() -> Path:
    return references_dir() / "library.json"


def runs_dir() -> Path:
    d = workspace_root() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_dir(run_id: str) -> Path:
    d = runs_dir() / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_events_file(run_id: str) -> Path:
    return run_dir(run_id) / "events.jsonl"


def run_renders_dir(run_id: str) -> Path:
    d = run_dir(run_id) / "renders"
    d.mkdir(parents=True, exist_ok=True)
    return d


def runs_index() -> Path:
    return runs_dir() / "index.json"
