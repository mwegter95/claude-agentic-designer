"""SSE event hub: ingests skill events (HTTP + JSONL tail), fans out to the UI.

Two ingestion paths converge here so the UI works whether or not the skill's
sandbox can reach this server over the network:

1. HTTP POST to /api/ingest (best-effort, low latency).
2. Tailing each run's events.jsonl (durable; the always-on source of truth).

Events are de-duplicated by a stable content hash, buffered per run (capped at
MAX_BUFFER), and pushed to every subscribed SSE client. Run status/score is derived
from the event stream and persisted to the run index.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.paths import runs_dir  # noqa: E402

from .storage import load_runs, save_runs  # noqa: E402

MAX_BUFFER = 3000  # matches the UI's 3000-log cap


def _hash_event(ev: dict) -> str:
    key = json.dumps(
        {
            "run_id": ev.get("run_id"),
            "seq": ev.get("seq"),
            "ts": ev.get("ts"),
            "type": ev.get("type"),
            "agent": ev.get("agent"),
            "message": ev.get("message"),
        },
        sort_keys=True,
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


class EventHub:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._buffers: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=MAX_BUFFER))
        self._seen: Dict[str, Set[str]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tail_positions: Dict[str, int] = {}

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ── subscription ────────────────────────────────────────────────────────
    async def subscribe(self, run_id: str | None) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        # Replay buffered history so a late-joining UI catches up.
        if run_id and run_id in self._buffers:
            for ev in list(self._buffers[run_id]):
                q.put_nowait(ev)
        else:
            for buf in self._buffers.values():
                for ev in list(buf):
                    q.put_nowait(ev)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    # ── ingestion ───────────────────────────────────────────────────────────
    def ingest(self, ev: dict) -> bool:
        run_id = ev.get("run_id")
        if not run_id:
            return False
        h = _hash_event(ev)
        seen = self._seen[run_id]
        if h in seen:
            return False
        seen.add(h)
        if len(seen) > MAX_BUFFER * 2:
            # bound memory; drop oldest hashes (approximate)
            self._seen[run_id] = set(list(seen)[-MAX_BUFFER:])
        self._buffers[run_id].append(ev)
        self._update_run_state(run_id, ev)
        self._broadcast(ev)
        return True

    def _broadcast(self, ev: dict) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(ev)
            except Exception:
                self._subscribers.discard(q)

    def _update_run_state(self, run_id: str, ev: dict) -> None:
        runs = load_runs()
        run = runs["runs"].get(run_id, {
            "run_id": run_id,
            "created_at": ev.get("ts", time.time()),
            "status": "running",
            "iterations": 0,
            "renders": [],
        })
        t = ev.get("type")
        data = ev.get("data", {}) or {}
        if t == "run_start":
            run["doc_type"] = data.get("doc_type")
            run["status"] = "running"
        elif t == "iteration":
            run["iterations"] = run.get("iterations", 0) + 1
        elif t == "evaluation":
            run["score"] = data.get("weighted_score")
            run["status"] = "passed" if data.get("passed") else "revise"
        elif t == "artifact":
            if data.get("kind") == "pptx" and data.get("out"):
                run["artifact"] = data["out"]
            renders = data.get("renders")
            if renders:
                run["renders"] = renders
        elif t == "run_end":
            if run.get("status") == "running":
                run["status"] = data.get("status", "passed")
        runs["runs"][run_id] = run
        save_runs(runs)

    def buffer(self, run_id: str) -> List[dict]:
        return list(self._buffers.get(run_id, []))

    # ── JSONL tailing (durable path) ─────────────────────────────────────────
    async def tail_loop(self) -> None:
        """Poll run event files for lines that never arrived via HTTP."""
        while True:
            try:
                base = runs_dir()
                for events_file in base.glob("*/events.jsonl"):
                    self._drain_file(events_file)
            except Exception:
                pass
            await asyncio.sleep(0.5)

    def _drain_file(self, path: Path) -> None:
        key = str(path)
        pos = self._tail_positions.get(key, 0)
        try:
            size = path.stat().st_size
        except OSError:
            return
        if size < pos:  # file truncated/rotated
            pos = 0
        if size == pos:
            return
        with path.open("r", encoding="utf-8") as fh:
            fh.seek(pos)
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.ingest(ev)
            self._tail_positions[key] = fh.tell()


hub = EventHub()
