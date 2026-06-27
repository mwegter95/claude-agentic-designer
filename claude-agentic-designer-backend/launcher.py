#!/usr/bin/env python3
"""launcher.py — entry point used by the Claude Desktop extension (.mcpb).

Claude Desktop spawns this over stdio (see manifest.json: `py -3 launcher.py`)
and expects the MCP handshake to start quickly. To stay fast and Windows-safe:

  * If dependencies are importable (the Windows bundle vendors them into ./lib at
    build time), we run the server **in-process** — no venv, no re-exec, so the
    stdio pipes Claude opened are preserved.
  * Only if deps are missing (e.g. a source-only bundle built on macOS) do we
    bootstrap a local venv and hand off to it as a child that inherits stdio.

It imports only the standard library so it runs under whatever Python Claude
Desktop launches. All real work lives in mcp_server.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE / "lib"                       # vendored deps in a packaged bundle
VENV_DIR = HERE / ".venv"
REQUIREMENTS = HERE / "requirements.txt"
SERVER = HERE / "mcp_server.py"
LOG = HERE / "workspace" / "logs" / "launcher.log"


def _log(msg: str) -> None:
    # stderr only — stdout is the MCP stdio channel. Also tee to a file so the
    # attach can be diagnosed even when the host swallows stderr.
    line = f"[launcher] {msg}"
    print(line, file=sys.stderr, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def _deps_importable() -> bool:
    try:
        import mcp  # noqa: F401
        return True
    except Exception:
        return False


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _ensure_venv() -> Path:
    py = _venv_python()
    if not py.exists():
        _log(f"creating virtual environment at {VENV_DIR} ...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    # Install requirements only when our marker file is missing/stale.
    marker = VENV_DIR / ".deps-installed"
    req_mtime = REQUIREMENTS.stat().st_mtime if REQUIREMENTS.exists() else 0.0
    if not marker.exists() or float(marker.read_text() or "0") < req_mtime:
        _log("installing requirements (first run may take a minute) ...")
        subprocess.run(
            [str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check",
             "-r", str(REQUIREMENTS)],
            check=True,
        )
        marker.write_text(str(req_mtime))
    return py


def main() -> int:
    if LIB.is_dir():
        sys.path.insert(0, str(LIB))
    sys.path.insert(0, str(HERE))
    _log(f"starting; interpreter={sys.executable}")
    selftest = os.environ.get("CLAUDE_DESIGNER_SELFTEST", "").strip().lower() \
        in ("1", "true", "yes", "on")

    # Fast path: deps already available -> run the server in this process so the
    # MCP stdio pipes Claude opened are preserved (no re-exec, Windows-safe).
    if _deps_importable():
        _log("dependencies available; starting MCP server in-process")
        try:
            import mcp_server  # noqa: E402  (deps are on sys.path now)
            if selftest:
                return mcp_server._selftest()
            mcp_server._run()
            return 0
        except Exception:  # noqa: BLE001
            import traceback
            _log("MCP server crashed:\n" + traceback.format_exc())
            return 1

    # Fallback: bootstrap a venv and run the server as a child that inherits our
    # stdio. Used for source-only bundles (e.g. built on macOS).
    _log("dependencies missing; bootstrapping a local environment")
    try:
        py = _ensure_venv()
    except subprocess.CalledProcessError as exc:
        _log(f"environment bootstrap failed: {exc}")
        return exc.returncode or 1

    env = dict(os.environ, CLAUDE_DESIGNER_BOOTSTRAPPED="1")
    proc = subprocess.run([str(py), str(SERVER)], env=env)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
