#!/usr/bin/env python3
"""mcp_server.py — Local MCP server for the Claude Agentic Designer.

This is the "MCP route": instead of running the workflow as a cloud Skill,
the workflow runs **locally on this PC** and the user drives it from the
Claude Desktop app. Claude Desktop launches this process over stdio and calls
its tools. Every tool reuses the same deterministic Python functions the Skill
uses and emits the same events, so the companion UI (FastAPI server + React
frontend) still lights up each agent in real time.

Architecture (all on the same machine):

    Claude Desktop  --stdio-->  mcp_server.py  --emit()-->  events.jsonl
                                      |                          |
                                      +---- HTTP POST ---->  FastAPI server  --SSE-->  React UI

Run it standalone for inspection:
    python mcp_server.py            # stdio transport (what Claude Desktop uses)
    mcp dev mcp_server.py           # MCP Inspector (if the `mcp` CLI is installed)

Remote route (Claude-for-PowerPoint add-in / web Custom Connector):
    Set CLAUDE_DESIGNER_MCP_TRANSPORT=sse (or streamable-http) and run this file to
    serve over HTTP, then expose it with a tunnel (see scripts/run_remote_mcp.*).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

# When packaged as a Claude Desktop extension (.mcpb), third-party deps are
# vendored into ./lib next to this file. Add it to the path if present.
_BUNDLED_LIB = REPO_ROOT / "lib"
if _BUNDLED_LIB.is_dir():
    sys.path.insert(0, str(_BUNDLED_LIB))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from tools.build_pptx import build  # noqa: E402
from tools.extract_tokens import extract  # noqa: E402
from tools.render_pptx import render, available_renderer  # noqa: E402
from tools.evaluate import run_evaluation  # noqa: E402
from tools.list_references import load as load_refs, resolve as resolve_ref  # noqa: E402
from tools.common.events import emit, AGENTS, EVENT_TYPES  # noqa: E402
from tools.common.paths import run_dir, run_renders_dir  # noqa: E402

SKILL_DIR = REPO_ROOT / "skill"
RUBRIC_DIR = SKILL_DIR / "rubrics"
DOC_TYPES = ("slides", "one_pager", "white_paper")

mcp = FastMCP("claude-agentic-designer")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _new_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rubric_path(doc_type: str) -> Path:
    if doc_type not in DOC_TYPES:
        raise ValueError(f"Unknown doc_type '{doc_type}'. Expected one of {DOC_TYPES}.")
    return RUBRIC_DIR / f"{doc_type}.rubric.json"


def _load_rubric(doc_type: str) -> dict:
    return json.loads(_rubric_path(doc_type).read_text(encoding="utf-8"))


def _enabled_references(enabled_only: bool = True, role: Optional[str] = None) -> dict:
    files = [resolve_ref(e) for e in load_refs()]
    if enabled_only:
        files = [f for f in files if f["enabled"]]
    if role:
        files = [f for f in files if f["role"] == role]
    masters = [f for f in files if f["role"] == "master"]
    examples = [f for f in files if f["role"] == "example"]
    needs_download = [
        f["name"] for f in files
        if not f["available"] and f["source"] == "sharepoint"
    ]
    return {
        "files": files,
        "master": masters[0] if masters else None,
        "examples": examples,
        "needs_download": needs_download,
    }


WORKFLOW_GUIDE = """\
# Claude Agentic Designer — MCP Workflow

You are orchestrating a small team of design agents to produce a polished
PowerPoint (or one-pager / white paper) that matches the user's brand master.
The golden rule: **LLMs plan; code renders.** You decide *what* goes on each
slide; the `build_presentation` tool fills the master's real placeholders. Never
invent geometry or free-draw shapes.

Use the `log_event` tool generously between every step so the companion UI lights
up each agent and shows your thinking. Valid agents: orchestrator, design_system,
content, structure, layout, builder, reflection, evaluator.

## Phases

0. **orchestrator** — Call `start_run(brief, doc_type)`. It returns a `run_id`,
   the enabled reference files, and the rubric. Pass `run_id` to every later call.
   `log_event` your plan: audience, key message, iteration budget (max 3).

1. **design_system** — Call `list_reference_files(role="master")` to find the
   brand master. Call `extract_design_tokens(run_id, master_path)` to pull the
   real palette, fonts, type scale, and layout catalog. `log_event` the style
   fingerprint you'll honor.

2. **content** — Draft the narrative: one idea per slide, executive-ready phrasing.
   `log_event` the outline.

3. **structure** — Map the narrative onto layouts from the token catalog (title,
   section header, stat callout, two-column, etc.). `log_event` the slide map.

4. **layout** — For each slide produce placeholder text keyed by the master's real
   placeholder indices, plus bullets and speaker notes. Assemble a `slide_plan`:
       {
         "doc_type": "<doc_type>",
         "master": "<absolute master path or omit>",
         "slides": [
           {"layout": <int or name>,
            "placeholders": {"0": "Title", "1": "Subtitle"},
            "bullets": {"1": ["point a", "point b"]},
            "notes": "speaker notes"}
         ]
       }

5. **builder** — Call `build_presentation(run_id, slide_plan)` to render the real
   .pptx. Then call `render_presentation(run_id)` to produce per-slide PNG previews
   (requires LibreOffice locally; it degrades gracefully if missing).

6. **reflection** — Review the rendered images critically. `log_event` concrete
   fixes (overflow, weak hierarchy, off-brand color). If you change anything,
   rebuild and re-render.

7. **evaluator** — Call `evaluate_presentation(run_id, doc_type, llm_scores)`.
   Provide `llm_scores` for the rubric's LLM-judged criteria (visual hierarchy,
   narrative flow) as {criterion_id: 0..1}. The tool runs the deterministic checks
   and merges your scores. If it fails and you have iterations left, loop back to
   reflection (emit an `iteration` event via `log_event` type="iteration").

8. **orchestrator** — When it passes (or you exhaust 3 iterations), call
   `finish_run(run_id, status, score, iterations, summary)` and tell the user where
   the .pptx is.
"""


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def start_run(brief: str, doc_type: str = "slides") -> dict:
    """Begin a new design run. Returns run_id, enabled references, and the rubric.

    Call this first. Pass the returned run_id to every subsequent tool so the
    companion UI groups events under one run.
    """
    if doc_type not in DOC_TYPES:
        raise ValueError(f"doc_type must be one of {DOC_TYPES}")
    run_id = _new_run_id()
    refs = _enabled_references(enabled_only=True)
    rubric = _load_rubric(doc_type)
    emit(run_id, "run_start", agent="orchestrator",
         message=f"Starting {doc_type} generation",
         data={"doc_type": doc_type, "brief": brief,
               "references": [f["name"] for f in refs["files"]]})
    return {
        "run_id": run_id,
        "doc_type": doc_type,
        "references": refs,
        "rubric": rubric,
        "workspace_run_dir": str(run_dir(run_id)),
    }


@mcp.tool()
def list_reference_files(enabled_only: bool = True, role: Optional[str] = None) -> dict:
    """List reference files (brand master + examples) the user has configured.

    role may be "master" or "example". Toggles set in the companion UI are honored.
    """
    return _enabled_references(enabled_only=enabled_only, role=role)


@mcp.tool()
def extract_design_tokens(run_id: str, master_path: str) -> dict:
    """Extract real design tokens (palette, fonts, type scale, layouts) from a master deck.

    Writes design_tokens.json into the run folder and returns the tokens.
    """
    emit(run_id, "tool_call", agent="design_system", message="extract_tokens",
         data={"master": Path(master_path).name})
    tokens = extract(Path(master_path).expanduser().resolve())
    out = run_dir(run_id) / "design_tokens.json"
    out.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    emit(run_id, "tool_result", agent="design_system",
         message=f"Extracted {len(tokens.get('layouts', []))} layout(s), "
                 f"{len(tokens.get('palette', []))} color(s)",
         data={"tokens_path": str(out)})
    return {"tokens": tokens, "tokens_path": str(out)}


@mcp.tool()
def build_presentation(run_id: str, slide_plan: dict) -> dict:
    """Build a real .pptx from a slide plan by filling the master's placeholders.

    The slide_plan must follow the slide_plan schema (doc_type, optional master,
    slides[] with layout/placeholders/bullets/notes). Returns the artifact path.
    """
    doc_type = slide_plan.get("doc_type", "slides")
    plan_path = run_dir(run_id) / "slide_plan.json"
    plan_path.write_text(json.dumps(slide_plan, indent=2), encoding="utf-8")
    emit(run_id, "tool_call", agent="builder", message="build_pptx",
         data={"doc_type": doc_type, "slides": len(slide_plan.get("slides", []))})
    out_path = run_dir(run_id) / f"{doc_type}.pptx"
    result = build(slide_plan, out_path, run_id=run_id)
    emit(run_id, "artifact", agent="builder",
         message=f"Generated {result['slides']} slide(s)",
         data={"out": result["out"], "kind": "pptx"})
    return result


@mcp.tool()
def render_presentation(run_id: str) -> dict:
    """Render the run's .pptx to per-slide PNG previews via LibreOffice.

    Degrades gracefully if LibreOffice is not installed (returns an error note).
    """
    pptx = next(run_dir(run_id).glob("*.pptx"), None)
    if pptx is None:
        return {"ok": False, "error": "No .pptx found for this run. Build it first."}
    if not available_renderer():
        emit(run_id, "log", agent="reflection", level="warn",
             message="No renderer (PowerPoint or LibreOffice) found; skipping preview render.")
        return {"ok": False,
                "error": "No renderer available. Install Microsoft PowerPoint "
                         "(Windows, used via COM) or LibreOffice.",
                "renders": [], "out": str(run_renders_dir(run_id))}
    emit(run_id, "tool_call", agent="reflection", message="render_pptx",
         data={"pptx": pptx.name})
    try:
        result = render(pptx, run_renders_dir(run_id), run_id=run_id)
    except Exception as exc:
        emit(run_id, "log", agent="reflection", level="error",
             message=f"Render failed: {exc}")
        return {"ok": False, "error": str(exc)}
    emit(run_id, "artifact", agent="reflection",
         message=f"Rendered {result['count']} preview image(s)",
         data={"kind": "renders", "renders": result["renders"]})
    return {"ok": True, **result}


@mcp.tool()
def evaluate_presentation(
    run_id: str,
    doc_type: str = "slides",
    llm_scores: Optional[dict] = None,
) -> dict:
    """Score the run's .pptx against the rubric (deterministic checks + your LLM scores).

    Provide llm_scores as {criterion_id: 0..1} for the rubric's LLM-judged criteria.
    Returns findings and a summary with weighted_score and passed.
    """
    pptx = next(run_dir(run_id).glob("*.pptx"), None)
    if pptx is None:
        return {"ok": False, "error": "No .pptx found for this run. Build it first."}
    rubric = _load_rubric(doc_type)
    plan_path = run_dir(run_id) / "slide_plan.json"
    tokens_path = run_dir(run_id) / "design_tokens.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    tokens = json.loads(tokens_path.read_text(encoding="utf-8")) if tokens_path.exists() else {}
    report = run_evaluation(rubric, plan, tokens, pptx,
                            llm_scores=llm_scores, run_id=run_id)
    out = run_dir(run_id) / "evaluation.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"ok": True, **report}


@mcp.tool()
def log_event(
    run_id: str,
    type: str,
    agent: str,
    message: str,
    level: str = "info",
    data: Optional[dict] = None,
) -> dict:
    """Narrate the workflow so the companion UI lights up.

    Use between every step. Valid `type` values: run_start, run_end, agent_start,
    agent_thinking, agent_end, tool_call, tool_result, log, artifact, evaluation,
    iteration. Valid `agent` values: orchestrator, design_system, content,
    structure, layout, builder, reflection, evaluator.
    """
    if type not in EVENT_TYPES:
        raise ValueError(f"type must be one of {EVENT_TYPES}")
    if agent not in AGENTS:
        raise ValueError(f"agent must be one of {AGENTS}")
    ev = emit(run_id, type, agent=agent, message=message, level=level, data=data or {})
    return {"ok": True, "seq": ev.get("seq")}


@mcp.tool()
def finish_run(
    run_id: str,
    status: str = "passed",
    score: Optional[float] = None,
    iterations: int = 1,
    summary: str = "",
) -> dict:
    """Close out a run. Emits run_end so the UI marks the run complete."""
    data: dict[str, Any] = {"status": status, "iterations": iterations}
    if score is not None:
        data["score"] = score
    if summary:
        data["summary"] = summary
    emit(run_id, "run_end", agent="orchestrator",
         level="info" if status == "passed" else "warn",
         message=summary or f"Run finished: {status}", data=data)
    pptx = next(run_dir(run_id).glob("*.pptx"), None)
    return {"ok": True, "run_id": run_id, "status": status,
            "artifact": str(pptx) if pptx else None}


@mcp.tool()
def get_workflow_guide(doc_type: str = "slides") -> str:
    """Return the full orchestration guide for the design workflow."""
    rubric = _load_rubric(doc_type)
    criteria = "\n".join(
        f"  - {c.get('id')} ({c.get('tier')}, weight {c.get('weight')}): {c.get('description', '')}"
        for c in rubric.get("criteria", [])
    )
    return (
        WORKFLOW_GUIDE
        + f"\n\n## Active rubric: {rubric.get('name')} "
        + f"(pass_threshold {rubric.get('pass_threshold')})\n{criteria}\n"
    )


# --------------------------------------------------------------------------- #
# Resources & prompt
# --------------------------------------------------------------------------- #
@mcp.resource("skill://workflow")
def workflow_resource() -> str:
    """The design workflow guide as a readable resource."""
    return WORKFLOW_GUIDE


@mcp.resource("skill://rubric/{doc_type}")
def rubric_resource(doc_type: str) -> str:
    """The rubric JSON for a given doc_type."""
    return _rubric_path(doc_type).read_text(encoding="utf-8")


@mcp.prompt()
def design_artifact(doc_type: str = "slides", brief: str = "") -> str:
    """Kick off a guided design run for the given doc_type and brief."""
    return (
        f"I want you to design a polished **{doc_type}** artifact using the "
        f"Claude Agentic Designer MCP tools.\n\nBrief: {brief or '(describe the goal, audience, and key message)'}\n\n"
        "Follow the workflow guide exactly. Start by calling `start_run`, then move "
        "through design_system -> content -> structure -> layout -> builder -> "
        "reflection -> evaluator, calling `log_event` between every step so the "
        "companion UI lights up. Loop on reflection/evaluation up to 3 times until "
        "the rubric passes, then call `finish_run`.\n\n"
        + WORKFLOW_GUIDE
    )


# --------------------------------------------------------------------------- #
# Transport runner
# --------------------------------------------------------------------------- #
def _truthy(val: str) -> bool:
    return val.strip().lower() in ("1", "true", "yes", "on")


def _port_open(host: str, port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def _venv_python() -> str:
    candidate = (
        REPO_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    return str(candidate) if candidate.exists() else sys.executable


def _child_env() -> dict:
    """Environment for spawned children so they can import vendored deps + tools."""
    env = dict(os.environ)
    parts = [str(REPO_ROOT)]
    if _BUNDLED_LIB.is_dir():
        parts.append(str(_BUNDLED_LIB))
    if env.get("PYTHONPATH"):
        parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def _has_built_ui() -> bool:
    """True if a prebuilt companion UI is present (served by the companion server)."""
    return (REPO_ROOT / "webui" / "index.html").is_file() \
        or (REPO_ROOT.parent / "dist" / "index.html").is_file()


def _spawn_detached(args, cwd: Path, log_path: Path, shell: bool = False,
                    env: Optional[dict] = None):
    import subprocess
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab", buffering=0)  # noqa: SIM115 (kept open for child)
    kwargs: dict[str, Any] = dict(cwd=str(cwd), stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=log, shell=shell)
    if env is not None:
        kwargs["env"] = env
    if os.name == "nt":
        # DETACHED_PROCESS: no console window, survives independently.
        kwargs["creationflags"] = 0x00000008
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(args, **kwargs)


def _autostart_companion_ui() -> None:
    """Best-effort: start the companion event server (FastAPI) and open the UI.

    Triggered when Claude Desktop launches this MCP server (or the remote runner)
    so the user does not have to start the UI by hand. Controlled by
    CLAUDE_DESIGNER_AUTOSTART_UI (default on). Never writes to stdout (the stdio
    MCP stream lives there) and never raises — UI is a convenience, not a
    dependency.

    The companion server serves a prebuilt UI (./webui) same-origin, so the
    packaged extension needs no Node/Vite at runtime. In local dev (no built UI
    but a Vite project one level up) it falls back to `npm run dev`.
    """
    if not _truthy(os.environ.get("CLAUDE_DESIGNER_AUTOSTART_UI", "1")):
        return

    host = os.environ.get("CLAUDE_DESIGNER_HOST", "127.0.0.1").strip() or "127.0.0.1"
    server_port = int(os.environ.get("CLAUDE_DESIGNER_PORT", "8787"))
    ui_port = int(os.environ.get("CLAUDE_DESIGNER_UI_PORT", "5273"))
    logs_dir = REPO_ROOT / "workspace" / "logs"
    frontend_dir = REPO_ROOT.parent  # the Vite project lives one level up (dev only)

    try:
        if not _port_open(host, server_port):
            _spawn_detached(
                [sys.executable, "-m", "uvicorn", "server.app:app",
                 "--host", host, "--port", str(server_port)],
                cwd=REPO_ROOT,
                log_path=logs_dir / "companion-server.log",
                env=_child_env(),
            )
            print(f"[mcp] launched companion server on http://{host}:{server_port}",
                  file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[mcp] companion server autostart skipped: {exc}", file=sys.stderr)

    # Packaged route: the companion server serves the built UI same-origin.
    if _has_built_ui():
        print(f"[mcp] companion UI served at http://{host}:{server_port}",
              file=sys.stderr)
        _open_browser_when_ready(f"http://{host}:{server_port}", host, server_port)
        return

    # Dev route: no built UI, but a Vite project with deps installed is available.
    try:
        if _truthy(os.environ.get("CLAUDE_DESIGNER_AUTOSTART_FRONTEND", "1")) \
                and not _port_open(host, ui_port):
            if (frontend_dir / "package.json").exists() \
                    and (frontend_dir / "node_modules").exists():
                if os.name == "nt":
                    _spawn_detached("npm run dev", cwd=frontend_dir,
                                    log_path=logs_dir / "frontend.log", shell=True)
                else:
                    _spawn_detached(["npm", "run", "dev"], cwd=frontend_dir,
                                    log_path=logs_dir / "frontend.log")
                print(f"[mcp] launched frontend (Vite) on http://{host}:{ui_port}",
                      file=sys.stderr)
                _open_browser_when_ready(f"http://{host}:{ui_port}", host, ui_port)
            else:
                print("[mcp] no built UI and no dev frontend found "
                      "(build with scripts/build_mcpb.* or run `npm install`).",
                      file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[mcp] frontend autostart skipped: {exc}", file=sys.stderr)


def _selftest() -> int:
    """Diagnostic run (CLAUDE_DESIGNER_SELFTEST=1): start the UI, probe, exit.

    Lets you reproduce the extension's startup outside Claude Desktop and see the
    real errors. Used by scripts/diagnose.ps1.
    """
    import time as _t
    print("[selftest] python    :", sys.version.replace("\n", " "), file=sys.stderr)
    print("[selftest] executable:", sys.executable, file=sys.stderr)
    print("[selftest] repo_root :", REPO_ROOT, file=sys.stderr)
    print("[selftest] bundled lib:", _BUNDLED_LIB if _BUNDLED_LIB.is_dir() else "(none)",
          file=sys.stderr)
    try:
        print("[selftest] renderer  :", available_renderer(), file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print("[selftest] renderer check failed:", exc, file=sys.stderr)
    print("[selftest] built UI  :", _has_built_ui(), file=sys.stderr)

    _autostart_companion_ui()

    host = os.environ.get("CLAUDE_DESIGNER_HOST", "127.0.0.1")
    sp = int(os.environ.get("CLAUDE_DESIGNER_PORT", "8787"))
    up = int(os.environ.get("CLAUDE_DESIGNER_UI_PORT", "5273"))
    for _ in range(20):  # up to ~10s for the server to bind
        if _port_open(host, sp):
            break
        _t.sleep(0.5)
    print(f"[selftest] server {host}:{sp} ->",
          "UP" if _port_open(host, sp) else "DOWN", file=sys.stderr)
    if not _has_built_ui():
        print(f"[selftest] vite   {host}:{up} ->",
              "UP" if _port_open(host, up) else "DOWN", file=sys.stderr)
    print("[selftest] see workspace/logs/ for companion-server.log / frontend.log",
          file=sys.stderr)
    print("[selftest] done", file=sys.stderr)
    return 0


def _open_browser_when_ready(url: str, host: str, port: int) -> None:
    if not _truthy(os.environ.get("CLAUDE_DESIGNER_OPEN_BROWSER", "1")):
        return
    import threading

    def _wait_and_open() -> None:
        import time as _t
        import webbrowser
        for _ in range(60):  # up to ~30s for the dev server to bind
            if _port_open(host, port):
                webbrowser.open(url)
                return
            _t.sleep(0.5)

    threading.Thread(target=_wait_and_open, daemon=True).start()


# stdio  -> Claude Desktop launches this process directly (local route).
# sse / streamable-http -> serve over HTTP so a tunnel (localtunnel/ngrok) can
#   expose it to Anthropic's cloud for the Claude-for-PowerPoint add-in (remote
#   route). In HTTP mode we add a tiny ASGI gateway that:
#     - optionally enforces a static Bearer token (CLAUDE_DESIGNER_MCP_TOKEN), and
#     - sets `bypass-tunnel-reminder: true` so localtunnel skips its interstitial
#       page (Anthropic's servers can't click through it).
def _gateway(app, token: str):
    """Pure-ASGI wrapper (does not buffer SSE streams)."""

    async def wrapped(scope, receive, send):
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        if token:
            headers = dict(scope.get("headers") or [])
            if headers.get(b"authorization", b"").decode() != f"Bearer {token}":
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"text/plain"),
                                (b"bypass-tunnel-reminder", b"true")],
                })
                await send({"type": "http.response.body", "body": b"Unauthorized"})
                return

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                hdrs = list(message.get("headers") or [])
                hdrs.append((b"bypass-tunnel-reminder", b"true"))
                message = {**message, "headers": hdrs}
            await send(message)

        await app(scope, receive, send_with_header)

    return wrapped


def _run() -> None:
    _autostart_companion_ui()
    transport = os.environ.get("CLAUDE_DESIGNER_MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
        return

    if transport not in ("sse", "streamable-http"):
        raise SystemExit(
            f"Unknown CLAUDE_DESIGNER_MCP_TRANSPORT '{transport}'. "
            "Use 'stdio', 'sse', or 'streamable-http'."
        )

    import uvicorn

    host = os.environ.get("CLAUDE_DESIGNER_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("CLAUDE_DESIGNER_MCP_PORT", "3333"))
    token = os.environ.get("CLAUDE_DESIGNER_MCP_TOKEN", "").strip()

    mcp.settings.host = host
    mcp.settings.port = port

    if transport == "streamable-http":
        base_app = mcp.streamable_http_app()
        route = mcp.settings.streamable_http_path
    else:
        base_app = mcp.sse_app()
        route = mcp.settings.sse_path

    app = _gateway(base_app, token)

    print(f"[mcp] Serving {transport} on http://{host}:{port}{route}", file=sys.stderr)
    if token:
        print("[mcp] Bearer auth ENABLED (Authorization: Bearer <token> required).",
              file=sys.stderr)
    else:
        print("[mcp] WARNING: no CLAUDE_DESIGNER_MCP_TOKEN set — endpoint is unauthenticated.",
              file=sys.stderr)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    _run()
