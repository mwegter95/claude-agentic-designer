"""Event model + emitter used by every skill tool.

Design goals:
- Zero hard third-party deps (urllib only) so it runs inside Claude's sandbox.
- Always durable: append JSON Lines to the run's events.jsonl.
- Best-effort live: POST to the local server so the UI lights up in real time.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from .paths import run_events_file

# Canonical agent ids — keep in sync with the frontend workflow graph.
AGENTS = [
    "orchestrator",
    "design_system",
    "content",
    "structure",
    "layout",
    "builder",
    "reflection",
    "evaluator",
]

EVENT_TYPES = [
    "run_start",
    "run_end",
    "agent_start",
    "agent_thinking",
    "agent_end",
    "tool_call",
    "tool_result",
    "log",
    "artifact",
    "evaluation",
    "iteration",
]

_seq_lock = threading.Lock()
_seq = 0


def _next_seq() -> int:
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq


@dataclass
class Event:
    run_id: str
    type: str
    seq: int = field(default_factory=_next_seq)
    ts: float = field(default_factory=lambda: time.time())
    agent: Optional[str] = None
    level: str = "info"  # debug | info | warn | error
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _post(event: Dict[str, Any]) -> None:
    url = os.environ.get(
        "CLAUDE_DESIGNER_EVENT_URL", "http://127.0.0.1:8787/api/ingest"
    )
    try:
        body = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=1.5)
    except Exception:
        # Best-effort only; the JSONL file is the durable source of truth.
        pass


def emit(
    run_id: str,
    type: str,
    *,
    agent: Optional[str] = None,
    message: str = "",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ev = Event(
        run_id=run_id,
        type=type,
        agent=agent,
        level=level,
        message=message,
        data=data or {},
    ).to_dict()

    # Durable append.
    try:
        path = run_events_file(run_id)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev) + "\n")
    except Exception:
        pass

    # Live (best-effort, non-blocking).
    threading.Thread(target=_post, args=(ev,), daemon=True).start()
    return ev
