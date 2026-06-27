"""FastAPI application entrypoint for Claude Agentic Designer.

Run:  uvicorn server.app:app --host 127.0.0.1 --port 8787
or:   python -m server.app
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .events_hub import hub  # noqa: E402
from .files_api import router as files_router  # noqa: E402
from .models import EventModel  # noqa: E402
from .runs_api import router as runs_router  # noqa: E402

app = FastAPI(title="Claude Agentic Designer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local companion UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router)
app.include_router(runs_router)


@app.on_event("startup")
async def _startup() -> None:
    hub.bind_loop(asyncio.get_event_loop())
    asyncio.create_task(hub.tail_loop())


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "claude-agentic-designer"}


@app.post("/api/ingest")
async def ingest(event: EventModel) -> dict:
    accepted = hub.ingest(event.model_dump())
    return {"ok": True, "accepted": accepted}


@app.get("/api/events/stream")
async def stream(request: Request, run_id: str | None = None) -> EventSourceResponse:
    queue = await hub.subscribe(run_id)

    async def event_gen():
        try:
            # Initial comment so the client knows the stream is live.
            yield {"event": "ready", "data": json.dumps({"run_id": run_id})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=15.0)
                    if run_id and ev.get("run_id") != run_id:
                        continue
                    yield {"event": "message", "data": json.dumps(ev)}
                except asyncio.TimeoutError:
                    # keep-alive ping
                    yield {"event": "ping", "data": "{}"}
        finally:
            hub.unsubscribe(queue)

    return EventSourceResponse(event_gen())


def main() -> None:
    import uvicorn

    host = os.environ.get("CLAUDE_DESIGNER_HOST", "127.0.0.1")
    port = int(os.environ.get("CLAUDE_DESIGNER_PORT", "8787"))
    uvicorn.run("server.app:app", host=host, port=port, reload=False)


# --------------------------------------------------------------------------- #
# Static companion UI (served same-origin so /api works with no CORS/proxy).
# Packaged extension: ./webui (prebuilt). Local dev fallback: ../dist.
# Registered LAST so it never shadows the /api routes above.
# --------------------------------------------------------------------------- #
def _webui_dir() -> Path | None:
    backend = Path(__file__).resolve().parents[1]
    for candidate in (backend / "webui", backend.parent / "dist"):
        if (candidate / "index.html").is_file():
            return candidate
    return None


_WEBUI = _webui_dir()
if _WEBUI is not None:
    _assets = _WEBUI / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/", include_in_schema=False)
    def _ui_index() -> FileResponse:
        return FileResponse(str(_WEBUI / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def _ui_spa(full_path: str) -> FileResponse:
        # Never let the SPA shadow API routes: unknown /api/* must 404, not
        # return index.html (which would break client error handling).
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Serve real static files; otherwise fall back to the SPA entry point.
        target = (_WEBUI / full_path).resolve()
        if _WEBUI in target.parents and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(_WEBUI / "index.html"))


if __name__ == "__main__":
    main()
