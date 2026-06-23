#!/usr/bin/env python3
"""list_references.py — Tell the skill which reference files to use this run.

This is the bridge between the companion UI's file picker and the Claude run. The
UI writes the reference library (uploads + SharePoint entries, each with a role and
an on/off toggle) to workspace/references/library.json. At the start of a run the
skill calls this tool to get the *enabled* entries and their on-disk paths, then
opens those actual files (master deck for token extraction; examples for visual
grounding).

It reads the library file directly, so it works even when the local server isn't
reachable from the skill's environment — as long as the workspace folder is visible.

Usage:
  python tools/list_references.py [--role master|example] [--enabled-only] [--run RUN]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.events import emit  # noqa: E402
from tools.common.paths import references_dir, references_index  # noqa: E402


def load() -> list[dict]:
    idx = references_index()
    if not idx.exists():
        return []
    try:
        data = json.loads(idx.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data.get("files", [])


def resolve(entry: dict) -> dict:
    local = entry.get("cached_path")
    if not local and entry.get("path"):
        local = str(references_dir() / entry["path"])
    available = bool(local and Path(local).exists())
    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "role": entry.get("role", "example"),
        "source": entry.get("source", "upload"),
        "enabled": bool(entry.get("enabled", True)),
        "url": entry.get("url"),
        "local_path": local,
        "available": available,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="List reference files for a run")
    p.add_argument("--role", choices=["master", "example"], default=None)
    p.add_argument("--enabled-only", action="store_true", default=True)
    p.add_argument("--all", dest="enabled_only", action="store_false")
    p.add_argument("--run", default="")
    args = p.parse_args()

    files = [resolve(e) for e in load()]
    if args.enabled_only:
        files = [f for f in files if f["enabled"]]
    if args.role:
        files = [f for f in files if f["role"] == args.role]

    masters = [f for f in files if f["role"] == "master"]
    examples = [f for f in files if f["role"] == "example"]
    unavailable = [f["name"] for f in files if not f["available"] and f["source"] == "sharepoint"]

    result = {
        "files": files,
        "master": masters[0] if masters else None,
        "examples": examples,
        "needs_download": unavailable,
    }

    if args.run:
        emit(args.run, "tool_result", agent="design_system",
             message=f"{len(files)} enabled reference(s): "
                     f"{len(masters)} master, {len(examples)} example(s)"
                     + (f"; needs download: {unavailable}" if unavailable else ""),
             data={"count": len(files)})

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
