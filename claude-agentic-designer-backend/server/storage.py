"""Tiny JSON-file persistence for the reference library and run index.

Deliberately dependency-free and process-safe enough for a single local server.
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.paths import references_index, runs_index  # noqa: E402

_lock = threading.Lock()


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_library() -> Dict[str, Any]:
    with _lock:
        return _read(references_index(), {"files": []})


def save_library(data: Dict[str, Any]) -> None:
    with _lock:
        _write(references_index(), data)


def load_runs() -> Dict[str, Any]:
    with _lock:
        return _read(runs_index(), {"runs": {}})


def save_runs(data: Dict[str, Any]) -> None:
    with _lock:
        _write(runs_index(), data)
