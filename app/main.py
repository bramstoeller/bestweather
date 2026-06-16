"""FastAPI app: API endpoints, the websocket, and SPA-style static serving.

Any unmatched path returns index.html so a place URL like
/Nederland/Gelderland/Nijmegen/strand resolves on the client.
"""

import mimetypes
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, geocoding
from .forecast import run_best_weather
from .providers import sources_meta
from .scoring import resolve_profile

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX = STATIC_DIR / "index.html"

app = FastAPI(title="AltijdMooiWeer", version=__version__)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__, "sources": sources_meta()})


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1), lang: str = "en") -> JSONResponse:
    try:
        results = await geocoding.search(q, lang)
    except Exception:  # noqa: BLE001 - never 500 on a flaky upstream
        results = []
    return JSONResponse({"results": results})


@app.get("/api/reverse")
async def api_reverse(lat: float, lon: float, lang: str = "en") -> JSONResponse:
    try:
        place = await geocoding.reverse(lat, lon, lang)
    except Exception:  # noqa: BLE001
        place = None
    return JSONResponse({"place": place})


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") != "subscribe":
                continue
            try:
                lat, lon = float(msg["lat"]), float(msg["lon"])
            except (KeyError, TypeError, ValueError):
                await ws.send_json({"type": "error", "message": "invalid coordinates"})
                continue
            profile = resolve_profile(msg.get("profile"))

            async def emit(payload: dict) -> None:
                await ws.send_json(payload)

            await run_best_weather(lat, lon, profile, emit)
    except WebSocketDisconnect:
        return


def _file(path: Path) -> FileResponse:
    media, _ = mimetypes.guess_type(str(path))
    if path.suffix == ".webmanifest":
        media = "application/manifest+json"
    return FileResponse(path, media_type=media)


@app.get("/{full_path:path}")
async def spa(full_path: str) -> FileResponse:
    if full_path:
        candidate = (STATIC_DIR / full_path).resolve()
        if candidate.is_file() and STATIC_DIR in candidate.parents:
            return _file(candidate)
    return _file(INDEX)
