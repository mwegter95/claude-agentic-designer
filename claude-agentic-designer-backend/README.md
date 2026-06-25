# claude-agentic-designer-backend

The **agentic workflow** behind Claude Agentic Designer — a Claude **Skill** plus a
local **FastAPI** event/orchestration server. It produces design-faithful PowerPoint
**one-pagers, white papers, and slide decks** that adhere to a master slide deck and
example designs, using a multi-agent **Generate → Reflect → Evaluate** loop with
explicit rubrics.

This repo is consumed two ways at once:

1. **As a Claude Skill** — drop it where Claude (Cowork / chat / PowerPoint plugin)
   discovers skills. Claude reads [`SKILL.md`](SKILL.md), plays each agent, and calls
   the deterministic Python tools in `tools/`.
2. **As a local server** — `server/` republishes the skill's verbose events over SSE
   to the companion UI (`claude-agentic-designer`) and manages the persistent
   reference library (master deck + examples) with Microsoft 365 / SharePoint support.

## Why it stays on-brand

| Principle | How it's enforced |
|-----------|-------------------|
| Master deck is a contract | `extract_tokens.py` derives palette, fonts, type scale, and the **named layout library** the agents must build against |
| LLMs plan, code renders | Agents emit `slide_plan.json`; `build_pptx.py` fills the master's real placeholders — **no free-drawing** |
| Reflection ≠ evaluation | Cheap self-critique first, then an **independent** rubric-scored gate |
| Two-tier rubric | Deterministic checks (fonts/colors/layouts/density) + LLM-judged visual/narrative criteria |
| Bounded loop | Max 3 iterations; always ship best-so-far + open issues |

## Layout

```
SKILL.md                     # the multi-agent workflow Claude executes
skill/
  agents/*.md                # per-agent role briefs
  rubrics/*.rubric.json      # one_pager / white_paper / slides scoring
  schemas/*.schema.json      # slide_plan + event contracts
tools/
  emit_event.py              # stream a verbose event to the UI (HTTP + JSONL)
  list_references.py         # resolve the UI's enabled master + examples for a run
  extract_tokens.py          # master.pptx -> design_tokens.json
  build_pptx.py              # slide_plan.json -> output.pptx (deterministic)
  render_pptx.py             # output.pptx -> PNGs (LibreOffice headless)
  evaluate.py                # deterministic rubric checks + LLM-score merge
  simulate_run.py            # demo: emit a full event stream with no Claude
  common/                    # shared paths/events/pptx helpers
server/
  app.py                     # FastAPI: /api/ingest, SSE /api/events/stream
  events_hub.py              # dedup + per-run buffer (cap 3000) + JSONL tail
  files_api.py               # reference library CRUD + on/off toggles
  graph_client.py            # Microsoft 365 / SharePoint via MSAL device code
  runs_api.py                # runs, renders, artifact download, M365 auth
workspace/                   # runtime data (references, runs) — gitignored
```

## Quick start

**macOS / Linux**

```bash
./scripts/install.sh         # venv + deps; warns if LibreOffice is missing
./scripts/run_server.sh      # http://127.0.0.1:8787  (SSE at /api/events/stream)
```

**Windows (PowerShell)**

```powershell
.\scripts\install.ps1        # venv + deps; warns if LibreOffice is missing
.\scripts\run_server.ps1     # http://127.0.0.1:8787  (SSE at /api/events/stream)
```

> If PowerShell blocks the scripts, allow them for the current user once with:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

Smoke-test the whole pipeline (and light up the UI) with **no Claude needed**:

```bash
# macOS / Linux
source .venv/bin/activate
python tools/simulate_run.py --doc-type slides --speed 0.25
```

```powershell
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
python tools\simulate_run.py --doc-type slides --speed 0.25
```

## Using it as a Claude Skill

1. Make this folder available to Claude as a skill (so `SKILL.md` is discoverable).
2. Start the server (above) and the companion UI so events have somewhere to go.
3. In Claude, ask for an on-brand artifact, e.g.
   *“Make a 6-slide executive deck on our platform consolidation using the master
   brand deck.”* Claude will run the agents, calling the `tools/*.py` scripts with a
   `--run` id; the UI lights up each agent and streams the logs.

The skill scripts always write `workspace/runs/<run_id>/events.jsonl` and *also*
best-effort POST to `CLAUDE_DESIGNER_EVENT_URL`. The server ingests whichever path
works, so the UI stays live even if the skill's sandbox can't reach localhost.

## Using it as a local MCP server (Claude Desktop)

This is the recommended route when you want to drive everything from the **Claude
Desktop app** while keeping all the local benefits — real `.pptx` files, your
reference library, and the companion UI lighting up each agent.

Unlike the cloud Skill (which runs in Claude's sandbox and can't reach your files
or local server), the MCP server runs **on your PC**. Claude Desktop launches it
over stdio and calls its tools; those tools reuse the exact same Python functions
and emit the exact same events, so nothing about the UI changes.

```
Claude Desktop ──stdio──▶ mcp_server.py ──emit()──▶ workspace/runs/<id>/events.jsonl
                                │                              │
                                └──── HTTP POST ────▶ FastAPI server ──SSE──▶ React UI
```

Everything runs on the same machine:

1. Install deps (includes the `mcp` SDK) and start the companion stack as usual:

   ```bash
   # macOS / Linux
   ./scripts/install.sh
   ./scripts/run_server.sh        # FastAPI server on :8787
   ```
   ```powershell
   # Windows (PowerShell)
   ./scripts/install.ps1
   ./scripts/run_server.ps1
   ```
   Then start the frontend (`../` React app) so the UI is open.

2. Point Claude Desktop at the MCP server. Copy the matching block from
   `claude_desktop_config.example.json` into your Claude Desktop config, fixing the
   absolute paths:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

   The `command` must be the venv's Python and `args` the absolute path to
   `mcp_server.py`. Restart Claude Desktop so it picks up the server.

3. In Claude Desktop, run the `design_artifact` prompt (or just chat). Claude calls
   the MCP tools — `start_run`, `list_reference_files`, `extract_design_tokens`,
   `build_presentation`, `render_presentation`, `evaluate_presentation`,
   `log_event`, `finish_run` — and the companion UI lights up each agent in real
   time. The finished `.pptx` lands in `workspace/runs/<run_id>/`.

To inspect the MCP server standalone (without Claude Desktop):

```bash
./scripts/run_mcp.sh      # uses the MCP Inspector if `mcp` CLI is present
```
```powershell
./scripts/run_mcp.ps1
```

## Microsoft 365 / SharePoint

Optional. Register a **public client** app in Entra ID with delegated
`Files.Read.All` + `Sites.Read.All`, then set `GRAPH_CLIENT_ID` (and
`GRAPH_TENANT_ID`) in `.env`. The UI signs in via device code, after which
SharePoint/OneDrive share URLs added to the library can be downloaded and used as
references. Without it, use local file uploads.

## Requirements

- **Python 3.10+** — macOS: `brew install python` · Windows: install from
  [python.org](https://www.python.org/downloads/) and check *“Add python.exe to PATH”*
  (or `winget install Python.Python.3.12`).
- **LibreOffice** (`soffice`) for slide rendering:
  - macOS: `brew install --cask libreoffice`
  - Windows: `winget install TheDocumentFoundation.LibreOffice` (or download from
    libreoffice.org). The scripts auto-detect
    `C:\Program Files\LibreOffice\program\soffice.exe`; otherwise set `SOFFICE_BIN`.
- **poppler** (`pdftoppm`) recommended for crisp per-slide PNGs:
  - macOS: `brew install poppler`
  - Windows: `winget install oschwartz10612.Poppler` (or download a poppler build and
    add its `bin` folder to PATH). Optional — without it the renderer falls back to a
    single PDF the UI can still link to.
