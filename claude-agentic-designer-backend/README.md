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

**Windows**

Double-click these (or run them from a terminal). They are `.bat` wrappers that
bypass the PowerShell execution policy and keep the window open so you can read the
output:

```text
scripts\install.bat        :: venv + deps (uses the 'py' launcher)
scripts\run_server.bat     :: http://127.0.0.1:8787  (SSE at /api/events/stream)
```

> **Don't double-click the `.ps1` files directly** — Windows blocks unsigned
> scripts by default, so the window just flashes and closes. Use the `.bat`
> wrappers above (or `start-all.bat` in the repo root to launch backend + frontend
> together). If you prefer running the `.ps1` from an open PowerShell window, allow
> them for the current user once with:
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

## Installing it as a Claude Desktop extension (.mcpb)

On a **managed/corporate** Claude account, the web "Add custom connector" option
(needed for the PowerPoint add-in's remote route) is often disabled by the admin.
**Desktop extensions are a separate, usually-allowed surface** — so this is the
route that works without a public tunnel or an admin connector exception.

> ⚠️ This installs in **Claude Desktop**, not the in-PowerPoint sidebar. You drive
> the workflow from Desktop chat; the tools still build the real `.pptx` and open it
> in PowerPoint (via COM on Windows). The sidebar UI specifically needs the blocked
> remote connector — the deck-building capability does not.

### Build the bundle

**Build on the same OS you'll install on.** The Windows build vendors native
dependencies into `./lib` so the installed extension starts **instantly** (no
first-run `pip install`, which would otherwise blow Claude's attach timeout):

```powershell
.\scripts\build_mcpb.ps1       # Windows  (recommended — vendors deps, instant start)
```
```bash
./scripts/build_mcpb.sh        # macOS / Linux (source-only; bootstraps a venv on first run)
```

This produces `claude-agentic-designer.mcpb` in the repo root.

> The bundle launches via the Windows Python launcher (`py -3`), since `python`
> is often not on PATH on Windows. To test the macOS bundle, change the manifest
> `command` to `python3` first.

### Install & use

1. Open **Claude Desktop → Settings → Extensions**.
2. Drag in (or double-click) `claude-agentic-designer.mcpb` and confirm install.
3. The extension **auto-starts the companion UI** — the FastAPI event server
   (`127.0.0.1:8787`) and the React frontend (`127.0.0.1:5273`), opening the
   browser automatically.
4. In Claude Desktop chat, ask it to design a deck. It calls the tools, the UI
   lights up each agent, and the finished `.pptx` opens in PowerPoint.

### Troubleshooting "Could not attach to MCP server"

Claude couldn't launch (or finish the handshake with) the server. Check, in order:

- **Wrong interpreter.** The manifest runs `py -3`. Confirm `py -3 --version` works
  in a terminal on that PC. If only `python`/`python3` exists, edit the manifest
  `command` to match and rebuild.
- **First-run timeout.** A source-only bundle installs deps on first launch, which
  can exceed the attach timeout. Build with `build_mcpb.ps1` on Windows so deps are
  vendored and startup is instant.
- **Read the log.** The launcher tees to `workspace/logs/launcher.log` inside the
  installed extension folder, and Claude Desktop keeps its own MCP logs
  (`%APPDATA%\Claude\logs\`). These show the real Python error.

### Auto-start controls (env, set in `manifest.json` or `.env`)

| Variable | Default | Effect |
| --- | --- | --- |
| `CLAUDE_DESIGNER_AUTOSTART_UI` | `1` | Master switch for the companion server + frontend |
| `CLAUDE_DESIGNER_AUTOSTART_FRONTEND` | `1` | Start the Vite UI (`npm run dev`) too |
| `CLAUDE_DESIGNER_OPEN_BROWSER` | `1` | Open the UI in the browser once it's up |
| `CLAUDE_DESIGNER_UI_PORT` | `5273` | Frontend port to probe/open |

Auto-start is best-effort and never blocks the MCP server: if a port is already
listening it's left alone, and if the frontend has no `node_modules` it's skipped
with a note (run `npm install` in the repo root once).

> **Skill (optional, hybrid pattern):** upload `SKILL.md` under Claude → Customize →
> Skills so Claude follows the brand/workflow rules while calling these tools.

## Using it from the Claude for PowerPoint add-in (remote route)

The PowerPoint add-in (and the Claude web app) talk to **Anthropic's cloud**, which
then calls your server over the **public internet** — it cannot reach `localhost` or
a stdio process. So for this route the MCP server runs over **HTTP (SSE)** behind a
tunnel with a constant address.

```
PowerPoint add-in ─▶ Anthropic cloud ─▶ https://<subdomain>.loca.lt/sse ─▶ your PC
                                              (localtunnel)        mcp_server.py (SSE)
```

### Skill vs. Connector — which is which

Anthropic uses these two words for two different things, and this project uses **both**:

- **Skill** = the instruction package (`SKILL.md`: the workflow, brand rules, the
  agent roles). It tells Claude *how to think and orchestrate*. You upload it under
  **Claude → Customize → Skills → Add skill**.
- **Connector** = the live server that *executes code* on your PC (builds the real
  `.pptx`, extracts tokens, renders previews, emits events to the UI). You add it
  under **Claude → Settings → Connectors → Add custom connector** as a **Remote MCP**
  URL. Claude reads the server's schema and turns its tools into callable skills,
  including inside the PowerPoint sidebar.

> Use the **hybrid pattern**: upload `SKILL.md` as a Skill *and* add the tunnel URL
> as a Connector. Claude follows the skill's rules while calling your local tools.

### Setup

1. **Configure `.env`** (copied from `.env.example`):
   ```
   CLAUDE_DESIGNER_MCP_TRANSPORT=sse
   CLAUDE_DESIGNER_MCP_PORT=3333
   CLAUDE_DESIGNER_MCP_TOKEN=<pick-a-long-random-secret>
   LT_SUBDOMAIN=claude-agentic-designer      # your constant address
   ```
   The token is **strongly recommended** — without it, anyone who finds your tunnel
   URL can run these tools on your machine.

2. **Start the tunnel + server** (Node.js is required; `npx` pulls localtunnel):
   ```bash
   # macOS / Linux
   ./scripts/run_remote_mcp.sh
   ```
   ```text
   :: Windows — double-click:
   scripts\run_remote_mcp.bat
   ```
   To start *everything* (companion server + frontend + tunnel) at once on Windows,
   double-click **`start-all.bat`** in the repo root — it now opens the frontend,
   backend, and the tunnel together. The Remote MCP window prints your public URL,
   e.g. `https://claude-agentic-designer.loca.lt/sse`.

3. **Add the Custom Connector in Claude** → Settings → Connectors → Add custom
   connector → Remote MCP / SSE:
   - **URL:** `https://<LT_SUBDOMAIN>.loca.lt/sse`
   - **Header:** `Authorization: Bearer <CLAUDE_DESIGNER_MCP_TOKEN>`
   The server auto-sends `bypass-tunnel-reminder: true` so Anthropic's cloud skips
   localtunnel's interstitial page (no manual IP/password step needed).

4. **Upload the Skill** → Claude → Customize → Skills → Add skill → upload `SKILL.md`.

5. **Use it in PowerPoint:** open the Claude add-in sidebar and trigger the skill
   (e.g. type your skill's slash command or just describe the deck). Keep the
   companion **frontend** open to watch the agents light up.

### Notes & caveats

- **Constant address:** localtunnel's `--subdomain` is *best-effort and free* — if the
  name is taken you'll get a random URL and must update the connector. For a
  guaranteed reserved domain, ngrok with a reserved domain is more reliable (point it
  at the same port; keep the bearer token and the connector header).
- **Security:** this connector lets a remote service run code on your PC (write files,
  drive PowerPoint). Always set `CLAUDE_DESIGNER_MCP_TOKEN`, keep the tunnel down when
  not in use, and never share the URL + token.
- **Plan:** Custom Connectors / the PowerPoint add-in require a paid Claude plan with
  the Connectors capability enabled.
- If a connector won't let you add a custom `Authorization` header, you can leave
  `CLAUDE_DESIGNER_MCP_TOKEN` blank (relying on the obscure tunnel URL only) — but that
  is far less safe; prefer ngrok/OAuth in that case.

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
- **A slide renderer** (for the preview thumbnails the Reflection/Evaluator agents
  use). The renderer is auto-detected in this order:
  1. **Microsoft PowerPoint** — *recommended on Windows.* If Office is already
     installed, no extra setup is needed; the backend drives PowerPoint via COM
     automation (`pywin32`, installed automatically on Windows). Highest fidelity.
  2. **LibreOffice** (`soffice`) — cross-platform fallback:
     - macOS: `brew install --cask libreoffice`
     - Windows: `winget install TheDocumentFoundation.LibreOffice`. Auto-detected at
       `C:\Program Files\LibreOffice\program\soffice.exe`; otherwise set `SOFFICE_BIN`.

  If neither is present, the `.pptx` is still generated and downloadable — only the
  preview images are skipped.
- **poppler** (`pdftoppm`) recommended for crisp per-slide PNGs **when using the
  LibreOffice path** (not needed for PowerPoint):
  - macOS: `brew install poppler`
  - Windows: `winget install oschwartz10612.Poppler` (or download a poppler build and
    add its `bin` folder to PATH). Optional — without it the renderer falls back to a
    single PDF the UI can still link to.
