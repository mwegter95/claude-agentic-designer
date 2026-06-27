#!/usr/bin/env python3
"""launcher.py — entry point used by the Claude Desktop extension (.mcpb).

Claude Desktop runs `python launcher.py`. Because a packaged extension ships
source-only (no platform binaries — pywin32/Pillow/lxml must be built on the
target machine), this launcher:

  1. ensures a local virtual environment exists next to the extension,
  2. installs requirements.txt into it on first run (so pywin32 runs its own
     Windows post-install correctly), and
  3. re-executes mcp_server.py with that venv's interpreter.

It deliberately imports only the standard library so it can run under whatever
Python Claude Desktop launches. All real work happens in mcp_server.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_DIR = HERE / ".venv"
REQUIREMENTS = HERE / "requirements.txt"
SERVER = HERE / "mcp_server.py"
_BOOTSTRAP_FLAG = "CLAUDE_DESIGNER_BOOTSTRAPPED"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _log(msg: str) -> None:
    # stderr only — stdout is the MCP stdio channel.
    print(f"[launcher] {msg}", file=sys.stderr, flush=True)


def _ensure_venv() -> Path:
    py = _venv_python()
    if not py.exists():
        _log(f"creating virtual environment at {VENV_DIR} ...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    # Install requirements only when our marker file is missing/stale.
    marker = VENV_DIR / ".deps-installed"
    req_mtime = REQUIREMENTS.stat().st_mtime if REQUIREMENTS.exists() else 0
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
    # Already running inside our venv? Just hand off to the server in-process.
    if os.environ.get(_BOOTSTRAP_FLAG) == "1":
        os.execv(sys.executable, [sys.executable, str(SERVER)])
        return 0  # unreachable

    try:
        py = _ensure_venv()
    except subprocess.CalledProcessError as exc:
        _log(f"environment bootstrap failed: {exc}")
        return exc.returncode or 1

    env = dict(os.environ, **{_BOOTSTRAP_FLAG: "1"})
    # Re-exec the server with the venv interpreter, inheriting stdio so the MCP
    # protocol stream is preserved.
    os.execve(str(py), [str(py), str(SERVER)], env)
    return 0  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
