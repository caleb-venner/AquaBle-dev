"""FastAPI service module for Chihiros BLE devices.

This module keeps only the web-facing FastAPI wiring. The BLE orchestration
is handled entirely functionally by core.dispatcher.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Try to configure unified logging early
try:
    from .logging_config import configure_logging
    configure_logging()
except Exception:
    pass

from . import spa
from .api.routes_commands import router as commands_router
from .api.routes_configurations import router as configurations_router
from .api.routes_devices import router as devices_router
from .api.routes_ha import router as ha_router
from .core.config import get_config_dir

logger = logging.getLogger(__name__)


class IngressIPRestrictionMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access to Ingress gateway IP when in Ingress mode."""

    INGRESS_GATEWAY_IP = "172.30.32.2"

    def __init__(self, app, ingress_enabled: bool = False):
        super().__init__(app)
        self.ingress_enabled = ingress_enabled

    async def dispatch(self, request: Request, call_next):
        if self.ingress_enabled:
            client_host = request.client.host if request.client else None
            if client_host in ("127.0.0.1", "localhost", "::1"):
                return await call_next(request)

            if client_host != self.INGRESS_GATEWAY_IP:
                return Response(
                    content="Access denied: Only Ingress connections allowed",
                    status_code=403,
                    media_type="text/plain",
                )
        return await call_next(request)


class IngressPathMiddleware(BaseHTTPMiddleware):
    """Middleware to capture and expose X-Ingress-Path header."""

    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path", "")
        request.state.ingress_path = ingress_path
        response = await call_next(request)
        if ingress_path:
            response.headers["X-AquaBle-Ingress-Path"] = ingress_path
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application state and resources via FastAPI lifespan."""
    # Our new functional model requires no background loop or heavy setup.
    # We just ensure the config directory is resolved and available in app state.
    app.state.config_dir = get_config_dir()
    logger.info(f"Using config directory: {app.state.config_dir}")
    
    # We could theoretically initialize proxy connections here if needed
    import json

    from .esphome_proxy import ESPHomeProxyManager, set_proxy_manager
    
    proxy_config_path = app.state.config_dir / "proxy.json"
    proxy_manager = None
    
    if proxy_config_path.exists():
        try:
            with open(proxy_config_path, encoding="utf-8") as f:
                proxy_conf = json.load(f)
            host = proxy_conf.get("host")
            if host:
                proxy_manager = ESPHomeProxyManager(
                    host=host,
                    password=proxy_conf.get("password", ""),
                    noise_psk=proxy_conf.get("noise_psk", "")
                )
                await proxy_manager.start()
                set_proxy_manager(proxy_manager)
                logger.info(f"Loaded ESPHome Proxy configuration for {host}")
        except Exception as e:
            logger.error(f"Failed to load proxy.json: {e}")

    yield

    if proxy_manager:
        await proxy_manager.stop()


app = FastAPI(title="Aquarium BLE Service", lifespan=lifespan)

INGRESS_ENABLED = bool(os.getenv("SUPERVISOR_TOKEN"))
if INGRESS_ENABLED:
    app.add_middleware(IngressIPRestrictionMiddleware, ingress_enabled=True)
    app.add_middleware(IngressPathMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker/HA monitoring."""
    return {
        "status": "healthy",
        "service": "aquable",
        "version": "1.2.3",
        "mode": "functional",
        "bluetooth": "available"
    }


# Re-export SPA constants
SPA_UNAVAILABLE_MESSAGE = spa.SPA_UNAVAILABLE_MESSAGE
SPA_DIST_AVAILABLE = spa.SPA_DIST_AVAILABLE
FRONTEND_DIST = spa.FRONTEND_DIST
PRIMARY_ENTRY = getattr(spa, "PRIMARY_ENTRY", "modern.html")
LEGACY_ENTRY = getattr(spa, "LEGACY_ENTRY", "index.html")

async def _proxy_dev_server(path: str) -> Response | None:
    return await spa._proxy_dev_server(path)


def _inject_base_tag_if_needed(request: Request, html_content: str) -> str:
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if not ingress_path:
        return html_content

    if not ingress_path.endswith("/"):
        ingress_path += "/"

    base_tag = f'<base href="{ingress_path}">'
    import re
    head_pattern = re.compile(r"(<head[^>]*>)", re.IGNORECASE)
    match = head_pattern.search(html_content)

    if match:
        insert_pos = match.end()
        html_content = html_content[:insert_pos] + "\\n    " + base_tag + html_content[insert_pos:]

    return html_content


spa.mount_assets(app)

@app.get("/", response_class=HTMLResponse)
async def serve_spa(request: Request) -> Response:
    if SPA_DIST_AVAILABLE:
        primary_path = FRONTEND_DIST / PRIMARY_ENTRY
        if primary_path.exists():
            html_content = primary_path.read_text(encoding="utf-8")
            html_content = _inject_base_tag_if_needed(request, html_content)
            return HTMLResponse(html_content)
        legacy_path = FRONTEND_DIST / LEGACY_ENTRY
        if legacy_path.exists():
            html_content = legacy_path.read_text(encoding="utf-8")
            html_content = _inject_base_tag_if_needed(request, html_content)
            return HTMLResponse(html_content)
            
    proxied = await _proxy_dev_server(f"/{PRIMARY_ENTRY}")
    if proxied is not None:
        return proxied
        
    return Response(
        SPA_UNAVAILABLE_MESSAGE,
        status_code=503,
        media_type="text/plain",
        headers={"cache-control": "no-store"},
    )


app.include_router(devices_router)
app.include_router(commands_router)
app.include_router(configurations_router)
app.include_router(ha_router)


@app.get("/{spa_path:path}", include_in_schema=False)
async def serve_spa_assets(spa_path: str, request: Request) -> Response:
    if not spa_path:
        raise HTTPException(status_code=404)
        
    first_segment = spa_path.split("/", 1)[0]
    if first_segment in {"api", "ui", "debug"} or spa_path in {
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
        from fastapi.responses import FileResponse
        return FileResponse(asset_path)
        
    if asset_path.is_dir():
        index_path = asset_path / "index.html"
        if index_path.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(index_path)
            
    if "." in spa_path:
        raise HTTPException(status_code=404)
        
    primary_path = FRONTEND_DIST / PRIMARY_ENTRY
    if primary_path.exists():
        html_content = primary_path.read_text(encoding="utf-8")
        html_content = _inject_base_tag_if_needed(request, html_content)
        return HTMLResponse(html_content)
        
    legacy_path = FRONTEND_DIST / LEGACY_ENTRY
    if legacy_path.exists():
        html_content = legacy_path.read_text(encoding="utf-8")
        html_content = _inject_base_tag_if_needed(request, html_content)
        return HTMLResponse(html_content)
        
    raise HTTPException(status_code=404)


def main() -> None:
    import sys

    import uvicorn
    try:
        from .logging_config import get_uvicorn_log_config
        log_config = get_uvicorn_log_config()
    except Exception:
        log_config = None

    tz = os.getenv("TZ", "UTC")
    is_ingress = bool(os.getenv("SUPERVISOR_TOKEN"))
    port = int(os.getenv("INGRESS_PORT", "8099" if is_ingress else "8000"))

    logger.info(f"Starting AquaBle with timezone: {tz}")
    logger.info(f"Ingress mode: {is_ingress}, listening on port: {port}")

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_config=log_config,
            access_log=True,
        )
    except Exception as e:
        import traceback
        logger.error(f"FATAL ERROR: {e}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
