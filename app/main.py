"""FastAPI application: static frontend, geocoding endpoints, and the websocket."""

from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, geocoding
from .forecast import run_best_weather
from .providers import active_providers

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="BestWeather", version=__version__)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "version": __version__,
            "providers": [p.name for p in active_providers()],
        }
    )


@app.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1), lang: str = "en"
) -> JSONResponse:
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
                lat = float(msg["lat"])
                lon = float(msg["lon"])
            except (KeyError, TypeError, ValueError):
                await ws.send_json({"type": "error", "message": "invalid coordinates"})
                continue

            async def emit(payload: dict) -> None:
                await ws.send_json(payload)

            await run_best_weather(lat, lon, emit)
    except WebSocketDisconnect:
        return


# Serve the static frontend at the root. Mounted last so it doesn't shadow /api.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
