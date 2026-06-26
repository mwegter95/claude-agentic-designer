#!/usr/bin/env python3
"""render_pptx.py — Rasterize a .pptx to PNG thumbnails for previews.

The Reflection and Evaluator agents need to *see* the rendered slides to judge
visual hierarchy and density; the frontend uses the PNGs for previews.

Two renderers are supported, tried in this order:
  1. Microsoft PowerPoint via COM automation (Windows only, no extra install if
     Office is present). Highest fidelity — uses the real PowerPoint engine.
  2. LibreOffice headless (`soffice`) — cross-platform fallback.
     macOS:  brew install --cask libreoffice
     Set SOFFICE_BIN to override auto-detection.

If neither is available, rendering is skipped gracefully (the .pptx is still
produced and downloadable; only the preview images are missing).

Usage:
  python tools/render_pptx.py --pptx run/output.pptx --out run/renders [--run RUN123]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common.events import emit  # noqa: E402

_CANDIDATES = [
    os.environ.get("SOFFICE_BIN", "").strip(),
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
    r"C:\Program Files\LibreOffice\program\soffice.exe",  # Windows
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",  # Windows (x86)
    shutil.which("soffice") or "",
    shutil.which("soffice.exe") or "",
    shutil.which("libreoffice") or "",
]


def find_soffice() -> Optional[str]:
    for c in _CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def _powerpoint_available() -> bool:
    """True only on Windows with pywin32 installed and PowerPoint registered."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
    except Exception:
        return False
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "PowerPoint.Application").Close()
        return True
    except Exception:
        return False


def available_renderer() -> Optional[str]:
    """Return the renderer that will be used: 'powerpoint', 'libreoffice', or None."""
    if _powerpoint_available():
        return "powerpoint"
    if find_soffice():
        return "libreoffice"
    return None


def _render_via_powerpoint(pptx: Path, out_dir: Path) -> List[Path]:
    """Export each slide to PNG using the installed PowerPoint via COM."""
    import pythoncom  # provided by pywin32
    import win32com.client

    pythoncom.CoInitialize()
    powerpoint = None
    presentation = None
    try:
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        # PowerPoint frequently refuses Visible=False; a brief window flash is
        # harmless and far more reliable than fighting it.
        try:
            powerpoint.Visible = True
        except Exception:
            pass
        presentation = powerpoint.Presentations.Open(
            str(pptx), ReadOnly=True, WithWindow=False
        )
        width, height = 1280, 720
        out_paths: List[Path] = []
        for i, slide in enumerate(presentation.Slides, start=1):
            target = out_dir / f"slide-{i:02d}.png"
            slide.Export(str(target), "PNG", width, height)
            out_paths.append(target)
        return sorted(out_paths)
    finally:
        try:
            if presentation is not None:
                presentation.Close()
        except Exception:
            pass
        try:
            if powerpoint is not None:
                powerpoint.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()


def _pdf_to_pngs(pdf: Path, out_dir: Path) -> List[Path]:
    """Use pdftoppm if available for per-page PNGs; otherwise convert via soffice."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        prefix = out_dir / "slide"
        subprocess.run(
            [pdftoppm, "-png", "-r", "120", str(pdf), str(prefix)],
            check=True, capture_output=True,
        )
        return sorted(out_dir.glob("slide-*.png"))
    return []


def _render_via_libreoffice(pptx: Path, out_dir: Path) -> List[Path]:
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice 'soffice' not found.")
    with tempfile.TemporaryDirectory() as tmp:
        # 1) pptx -> pdf
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(pptx)],
            check=True, capture_output=True,
        )
        pdf = next(Path(tmp).glob("*.pdf"), None)
        if pdf is None:
            raise RuntimeError("LibreOffice did not produce a PDF.")
        # 2) pdf -> per-slide PNGs
        pngs = _pdf_to_pngs(pdf, out_dir)
        if not pngs:
            # Fallback: keep the PDF so the UI still has something to show.
            shutil.copy(pdf, out_dir / "deck.pdf")
    return sorted(out_dir.glob("*.png"))


def render(pptx: Path, out_dir: Path, run_id: str = "") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    renderer = available_renderer()
    if renderer is None:
        raise RuntimeError(
            "No slide renderer available. On Windows, install Microsoft PowerPoint "
            "(used via COM, no extra setup) or LibreOffice; set SOFFICE_BIN to override."
        )
    if renderer == "powerpoint":
        _render_via_powerpoint(pptx, out_dir)
    else:
        _render_via_libreoffice(pptx, out_dir)
    files = [p.name for p in sorted(out_dir.glob("*.png"))]
    result = {"renders": files, "out": str(out_dir), "count": len(files),
              "renderer": renderer}
    if run_id:
        emit(run_id, "tool_result", agent="reflection",
             message=f"Rendered {len(files)} slide image(s) via {renderer}",
             data=result)
    return result



def main() -> int:
    p = argparse.ArgumentParser(description="Render .pptx to PNGs via LibreOffice")
    p.add_argument("--pptx", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--run", default="")
    args = p.parse_args()

    pptx = Path(args.pptx).expanduser().resolve()
    if not pptx.exists():
        print(f"PPTX not found: {pptx}", file=sys.stderr)
        return 2

    if args.run:
        emit(args.run, "tool_call", agent="reflection", message="render_pptx",
             data={"pptx": pptx.name})

    try:
        result = render(pptx, Path(args.out).expanduser().resolve(), run_id=args.run)
    except Exception as exc:  # surface render failures to the UI without crashing
        if args.run:
            emit(args.run, "log", agent="reflection", level="error",
                 message=f"Render failed: {exc}")
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    print(json.dumps({"ok": True, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
