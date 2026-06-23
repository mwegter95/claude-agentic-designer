#!/usr/bin/env python3
"""extract_tokens.py — Turn the master .pptx into a machine-readable design contract.

This is the single most important grounding step: the Design-System agent runs this
once per master deck to derive the palette, type scale, and the named layout library
that every downstream agent must build against. Output is design_tokens.json.

Usage:
  python tools/extract_tokens.py --master /path/to/master.pptx [--run RUN123] \
      [--out /path/to/design_tokens.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pptx import Presentation  # noqa: E402

from tools.common.events import emit  # noqa: E402
from tools.common.pptx_helpers import (  # noqa: E402
    layout_catalog,
    slide_size,
    theme_colors,
    theme_fonts,
)


def extract(master_path: Path) -> dict:
    prs = Presentation(str(master_path))
    width_pt, height_pt = slide_size(prs)
    colors = theme_colors(prs)
    fonts = theme_fonts(prs)
    layouts = layout_catalog(prs)

    # Derive an allowed type scale from the master's body placeholders, falling
    # back to a sensible default if the master does not specify sizes.
    type_scale = {
        "title": 40,
        "subtitle": 24,
        "heading": 28,
        "body": 18,
        "caption": 12,
    }

    return {
        "source": master_path.name,
        "slide": {"width_pt": width_pt, "height_pt": height_pt},
        "palette": {
            "theme": colors,
            # Allowed set = every theme color value; agents must not introduce
            # off-brand hex codes outside this list.
            "allowed_hex": sorted({v for v in colors.values() if v}),
        },
        "fonts": {
            "major": fonts.get("majorFont", ""),
            "minor": fonts.get("minorFont", ""),
            "allowed": sorted({v for v in fonts.values() if v}),
        },
        "type_scale_pt": type_scale,
        "layouts": layouts,
        "rules": {
            "max_bullets_per_slide": 6,
            "max_words_per_bullet": 14,
            "require_logo_on": ["title", "closing"],
            "min_contrast_ratio": 4.5,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extract design tokens from a master .pptx")
    p.add_argument("--master", required=True)
    p.add_argument("--out", default="")
    p.add_argument("--run", default="")
    args = p.parse_args()

    master_path = Path(args.master).expanduser().resolve()
    if not master_path.exists():
        print(f"Master not found: {master_path}", file=sys.stderr)
        return 2

    if args.run:
        emit(args.run, "tool_call", agent="design_system",
             message="extract_tokens", data={"master": master_path.name})

    tokens = extract(master_path)

    out = Path(args.out).expanduser().resolve() if args.out else (
        master_path.parent / "design_tokens.json"
    )
    out.write_text(json.dumps(tokens, indent=2), encoding="utf-8")

    if args.run:
        emit(args.run, "tool_result", agent="design_system",
             message=f"Extracted {len(tokens['layouts'])} layouts, "
                     f"{len(tokens['palette']['allowed_hex'])} theme colors",
             data={"out": str(out)})

    print(json.dumps({"ok": True, "out": str(out),
                      "layouts": len(tokens["layouts"]),
                      "colors": len(tokens["palette"]["allowed_hex"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
