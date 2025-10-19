"""Helpers to mount and serve the frontend SPA (built or via dev server).

DEV SERVER PROXY USAGE:
    The dev server proxy is for LOCAL DEVELOPMENT ONLY. It allows developers
    to run the Vite dev server (npm run dev) and have the backend proxy requests
    to it for hot module reloading.
    
    In production (Home Assistant add-on), only built static assets are served.
    The add-on build process creates the frontend/dist directory, and the proxy
    logic is never used.
    
    Environment variable:
        AQUA_BLE_FRONTEND_DEV: URL of dev server (e.g., "http://localhost:5173")
                               Set to "0" to explicitly disable proxy
                               Automatically disabled when SUPERVISOR_TOKEN is present
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_FRONTEND_DIST = PACKAGE_ROOT.parent.parent / "frontend" / "dist"
FRONTEND_DIST = Path(
    os.getenv("AQUA_BLE_FRONTEND_DIST", str(DEFAULT_FRONTEND_DIST))
    or str(DEFAULT_FRONTEND_DIST)
)
SPA_DIST_AVAILABLE = FRONTEND_DIST.exists()

PRIMARY_ENTRY = "modern.html"
LEGACY_ENTRY = "index.html"

SPA_UNAVAILABLE_MESSAGE = (
    "The TypeScript dashboard is unavailable. "
    "Build the SPA (npm run build) or start the dev server (npm run dev) "
    "before visiting '/' again."
)


# Disable dev server proxy in Home Assistant add-on (production)
if os.getenv("SUPERVISOR_TOKEN"):
    DEV_SERVER_CANDIDATES: tuple[httpx.URL, ...] = ()
else:
    _DEV_SERVER_ENV = (os.getenv("AQUA_BLE_FRONTEND_DEV", "") or "").strip()
    if _DEV_SERVER_ENV == "0":
        DEV_SERVER_CANDIDATES = ()
    elif _DEV_SERVER_ENV:
        DEV_SERVER_CANDIDATES = (httpx.URL(_DEV_SERVER_ENV.rstrip("/")),)
    else:
        DEV_SERVER_CANDIDATES = (
            httpx.URL("http://127.0.0.1:5173"),
            httpx.URL("http://localhost:5173"),
        )

DEV_SERVER_TIMEOUT = httpx.Timeout(connect=1.0, read=5.0, write=5.0, pool=1.0)
_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


def mount_assets(app) -> None:
    """Mount the '/assets' static path if a built SPA is available."""
    if SPA_DIST_AVAILABLE:
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="spa-assets",
            )


def _read_entry(name: str) -> HTMLResponse | None:
    entry_path = FRONTEND_DIST / name
    if entry_path.exists():
        return HTMLResponse(entry_path.read_text(encoding="utf-8"))
    return None


async def serve_index_or_proxy() -> Response:
    """Serve built index.html or proxy to a running dev server."""
    if SPA_DIST_AVAILABLE:
        entry_response = _read_entry(PRIMARY_ENTRY) or _read_entry(LEGACY_ENTRY)
        if entry_response is not None:
            return entry_response
    proxied = await _proxy_dev_server(f"/{PRIMARY_ENTRY}")
    if proxied is not None:
        return proxied
    return Response(
        SPA_UNAVAILABLE_MESSAGE,
        status_code=503,
        media_type="text/plain",
        headers={"cache-control": "no-store"},
    )


async def serve_spa_asset(spa_path: str) -> Response:
    """Serve a built asset or proxy/fallback appropriately for client routes."""
    if not spa_path:
        raise HTTPException(status_code=404)

    first_segment = spa_path.split("/", 1)[0]
    if first_segment in {"api"} or spa_path in {
        "docs",
        "redoc",
        "openapi.json",
    }:
        raise HTTPException(status_code=404)

    if not SPA_DIST_AVAILABLE:
        proxied = await _proxy_dev_server(f"/{spa_path}")
        if proxied is not None:
            return proxied
        raise HTTPException(status_code=404, detail="SPA bundle unavailable")

    asset_path = FRONTEND_DIST / spa_path
    if asset_path.is_file():
        return FileResponse(asset_path)

    if asset_path.is_dir():
        index_path = asset_path / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)

    if "." in spa_path:
        raise HTTPException(status_code=404)

    entry_response = _read_entry(PRIMARY_ENTRY) or _read_entry(LEGACY_ENTRY)
    if entry_response is not None:
        return entry_response

    raise HTTPException(status_code=404)


async def _proxy_dev_server(path: str) -> Optional[Response]:
    """Try to fetch a path from the Vite dev server if configured."""
    if not DEV_SERVER_CANDIDATES:
        return None
    normalized = path if path.startswith("/") else f"/{path}"
    for base_url in DEV_SERVER_CANDIDATES:
        try:
            async with httpx.AsyncClient(
                base_url=str(base_url), timeout=DEV_SERVER_TIMEOUT
            ) as client:
                response = await client.get(normalized, follow_redirects=True)
        except httpx.HTTPError:
            continue
        headers = {
            key: value for key, value in response.headers.items() if key.lower() not in _HOP_HEADERS
        }
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers,
        )
    return None
