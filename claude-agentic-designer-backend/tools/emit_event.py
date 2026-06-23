#!/usr/bin/env python3
"""emit_event.py — CLI the Claude Skill calls to stream a verbose event to the UI.

Claude invokes this at every agent transition, thought, and tool use so the
frontend can light up the active agent and append to the logs panel.

Examples:
  python tools/emit_event.py --run RUN123 --type agent_start --agent content \
      --message "Drafting narrative for executive audience"

  python tools/emit_event.py --run RUN123 --type agent_thinking --agent layout \
      --message "Mapping 'stat callout' block to master layout #7" --level debug

  python tools/emit_event.py --run RUN123 --type tool_call --agent builder \
      --message "build_pptx" --data '{"slides": 12}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.events import AGENTS, EVENT_TYPES, emit  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Emit a Claude Agentic Designer event.")
    p.add_argument("--run", required=True, help="Run id")
    p.add_argument("--type", required=True, choices=EVENT_TYPES)
    p.add_argument("--agent", choices=AGENTS, default=None)
    p.add_argument("--message", default="")
    p.add_argument("--level", default="info", choices=["debug", "info", "warn", "error"])
    p.add_argument("--data", default="", help="Optional JSON object string")
    args = p.parse_args()

    data = {}
    if args.data.strip():
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as exc:
            print(f"Invalid --data JSON: {exc}", file=sys.stderr)
            return 2

    ev = emit(
        args.run,
        args.type,
        agent=args.agent,
        message=args.message,
        level=args.level,
        data=data,
    )
    print(json.dumps({"ok": True, "seq": ev["seq"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
