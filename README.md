# Claude Agentic Designer — Companion UI

The live cockpit for the [`claude-agentic-designer-backend`](../claude-agentic-designer-backend)
agentic workflow. It visualizes the multi-agent pipeline, lights up each agent as it
runs, streams verbose logs (up to **3,000**), and manages the **reference designs**
(master deck + examples) that ground every run.

Built with **React + TypeScript + Tailwind + Vite**.

## What you see

```
┌───────────────────────────────────────────────┬───────────────────┐
│  Workflow canvas — 8 agents, edges light up    │  Run              │
│  as the active agent works, with a revise loop │  status · score   │
│                                                │  · downloads      │
│                                                │  · slide previews │
├────────────────────────────────────────────────┤───────────────────┤
│  Logs (lower-left) — verbose per-agent thinking │  Reference        │
│  + tool use, color-coded, filter/search, 3000   │  Designs          │
│  cap, expandable JSON payloads, auto-scroll     │  upload / SP URLs │
│                                                │  on/off toggles   │
└────────────────────────────────────────────────┴───────────────────┘
```

- **Workflow canvas** — Orchestrator → Design-System → Content → Structure → Layout →
  Builder → Reflection → Evaluator, with a dashed **revise loop** back to Layout. The
  active agent pulses; completed agents settle; the incoming edge animates.
- **Logs panel** (lower-left) — every event the skill emits: `agent_thinking`,
  `tool_call`, `tool_result`, `evaluation`, etc. Color-coded by agent and level,
  filterable, searchable, capped at 3,000, with expandable `data` payloads.
- **Reference Designs** — upload `.pptx`/`.potx`/`.pdf`/images **or** paste
  SharePoint/OneDrive share URLs. Each entry is tagged **master** or **example**,
  **persists across runs**, and has an on/off toggle controlling whether it's
  referenced for a run. Microsoft 365 sign-in (device code) enables SharePoint
  downloads.
- **Run panel** — doc type, rubric score, iteration count, `.pptx` download, and
  slide-image previews.

## Run it

```bash
npm install
npm run dev          # http://localhost:5273  (proxies /api -> 127.0.0.1:8787)
```

Start the backend first (see the backend README) so the UI has a live SSE stream.
With no live Claude run, drive the UI from the backend simulator:

```bash
# in the backend repo, with its venv active
python tools/simulate_run.py --speed 0.25
```

Watch the agents light up and the logs fill in real time.

## How it connects

- **SSE**: subscribes to `GET /api/events/stream`; reconnects with backoff. Events
  are grouped per run; the newest run is auto-followed (pick others from the Run
  dropdown).
- **REST**: reference library CRUD, run/artifact/render fetch, and Microsoft 365
  device-code auth — all under `/api`.
- **Config**: dev uses Vite's proxy. For a standalone build pointing elsewhere, set
  `VITE_API_BASE` (e.g. `VITE_API_BASE=http://127.0.0.1:8787 npm run build`).

## Build

```bash
npm run build        # tsc --noEmit + vite build -> dist/
npm run preview
```
