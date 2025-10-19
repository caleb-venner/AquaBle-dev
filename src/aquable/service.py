"""FastAPI service module for Chihiros BLE devices.

This module keeps only the web-facing FastAPI wiring. The BLE orchestration
implementation (CachedStatus, BLEService and persistence helpers) has been
extracted to ``ble_service.py`` to improve modularity. We import the
implementation and expose the same public names for backwards compatibility.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Ensure the implementation module picks up any env override when this
# module is reloaded during tests (the tests set AQUA_BLE_STATUS_WAIT
# then reload this module expecting the constant to reflect the env var).
from . import ble_service as _ble_impl
from . import spa
from .api.routes_commands import router as commands_router
from .api.routes_configurations import router as configurations_router
from .api.routes_devices import router as devices_router
from .ble_service import BLEService
from .config_migration import get_env_float

try:
    _ble_impl.STATUS_CAPTURE_WAIT_SECONDS = get_env_float(
        "AQUA_BLE_STATUS_WAIT",
        _ble_impl.STATUS_CAPTURE_WAIT_SECONDS,
    )
except Exception:
    # Be conservative: if parsing fails, leave the implementation default.
    pass

# Global service instance - initialized lazily on first access
_service_instance: BLEService | None = None


def get_service() -> BLEService:
    """Get or create the singleton BLE service instance.
    
    This lazy initialization prevents double-initialization when uvicorn
    imports the module in both main and worker processes.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = BLEService()
    return _service_instance


# Back-compat: export service instance for tests
service = get_service()


class IngressIPRestrictionMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access to Ingress gateway IP when in Ingress mode.
    
    Home Assistant Ingress requires that add-ons only accept connections from
    the Ingress gateway at 172.30.32.2. This middleware enforces that restriction
    when the add-on is running in Ingress mode (detected by SUPERVISOR_TOKEN env var).
    """
    
    INGRESS_GATEWAY_IP = "172.30.32.2"
    
    def __init__(self, app, ingress_enabled: bool = False):
        super().__init__(app)
        self.ingress_enabled = ingress_enabled
    
    async def dispatch(self, request: Request, call_next):
        # Only enforce IP restriction when Ingress is enabled
        if self.ingress_enabled:
            client_host = request.client.host if request.client else None
            
            # Allow health checks from localhost for Docker/HA monitoring
            if client_host in ("127.0.0.1", "localhost", "::1"):
                return await call_next(request)
            
            # Enforce Ingress gateway IP restriction
            if client_host != self.INGRESS_GATEWAY_IP:
                return Response(
                    content="Access denied: Only Ingress connections allowed",
                    status_code=403,
                    media_type="text/plain"
                )
        
        return await call_next(request)


class IngressPathMiddleware(BaseHTTPMiddleware):
    """Middleware to capture and expose X-Ingress-Path header.
    
    Home Assistant Ingress adds the X-Ingress-Path header to all requests,
    which contains the base path for the add-on. This middleware makes it
    available to the application for constructing proper URLs if needed.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Capture X-Ingress-Path header if present
        ingress_path = request.headers.get("X-Ingress-Path", "")
        
        # Store in request state for potential use by handlers
        request.state.ingress_path = ingress_path
        
        # Add custom header to response for debugging/frontend use
        response = await call_next(request)
        if ingress_path:
            response.headers["X-AquaBle-Ingress-Path"] = ingress_path
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage BLE service startup and shutdown via FastAPI lifespan."""
    # Initialize service lazily - only in the worker process that handles requests
    service = get_service()
    # Make service instance available to routers
    app.state.service = service
    await service.start()
    try:
        yield
    finally:
        await service.stop()


app = FastAPI(title="Aquarium BLE Service", lifespan=lifespan)

# Add Ingress middleware if running under Home Assistant Supervisor
# The SUPERVISOR_TOKEN environment variable is set by Home Assistant for all add-ons
INGRESS_ENABLED = bool(os.getenv("SUPERVISOR_TOKEN"))
if INGRESS_ENABLED:
    # Add path middleware first to capture X-Ingress-Path header
    app.add_middleware(IngressPathMiddleware)
    # Then add IP restriction to enforce security
    app.add_middleware(IngressIPRestrictionMiddleware, ingress_enabled=True)


# Health check endpoint for container monitoring
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker/HA monitoring."""
    try:
        # Basic service availability check
        cached_statuses = get_service().get_status_snapshot()
        device_count = len(cached_statuses)
        return {
            "status": "healthy",
            "service": "aquable",
            "version": "1.0.0",
            "devices": {
                "cached": device_count,
                "status": "available" if device_count > 0 else "no_devices",
            },
            "bluetooth": "available",  # Could enhance with actual BLE adapter check
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "aquable",
        }


# Back-compat constants and helpers for tests
SPA_UNAVAILABLE_MESSAGE = getattr(spa, "SPA_UNAVAILABLE_MESSAGE")
SPA_DIST_AVAILABLE = getattr(spa, "SPA_DIST_AVAILABLE")
FRONTEND_DIST = getattr(spa, "FRONTEND_DIST")
PRIMARY_ENTRY = getattr(spa, "PRIMARY_ENTRY", "modern.html")
LEGACY_ENTRY = getattr(spa, "LEGACY_ENTRY", "index.html")


async def _proxy_dev_server(path: str) -> Response | None:
    return await spa._proxy_dev_server(path)


def _inject_base_tag_if_needed(request: Request, html_content: str) -> str:
    """Inject <base> tag into HTML if serving through Ingress.
    
    When Home Assistant Ingress proxies requests, it adds X-Ingress-Path header
    containing the base path (e.g., '/api/hassio_ingress/xyz123'). We need to
    inject a <base> tag so that relative asset paths resolve correctly.
    """
    # Check if request came through Ingress
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if not ingress_path:
        return html_content
    
    # Ensure ingress_path ends with /
    if not ingress_path.endswith("/"):
        ingress_path += "/"
    
    # Inject base tag after <head> opening tag
    base_tag = f'<base href="{ingress_path}">'
    
    # Find <head> tag and inject base tag right after it
    import re
    head_pattern = re.compile(r'(<head[^>]*>)', re.IGNORECASE)
    match = head_pattern.search(html_content)
    
    if match:
        # Insert base tag right after <head>
        insert_pos = match.end()
        html_content = (
            html_content[:insert_pos] +
            '\n    ' + base_tag +
            html_content[insert_pos:]
        )
    
    return html_content


# Mount SPA assets via helper module
spa.mount_assets(app)


@app.get("/", response_class=HTMLResponse)
async def serve_spa(request: Request) -> Response:
    """Serve SPA index or proxy to dev server; mirrors legacy behavior for tests."""
    # Use local constants to support monkeypatching in tests
    if SPA_DIST_AVAILABLE:
        primary_path = FRONTEND_DIST / PRIMARY_ENTRY
        if primary_path.exists():
            html_content = primary_path.read_text(encoding="utf-8")
            # Inject base tag for Ingress if X-Ingress-Path is present
            html_content = _inject_base_tag_if_needed(request, html_content)
            return HTMLResponse(html_content)
        legacy_path = FRONTEND_DIST / LEGACY_ENTRY
        if legacy_path.exists():
            html_content = legacy_path.read_text(encoding="utf-8")
            # Inject base tag for Ingress if X-Ingress-Path is present
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


# Startup/shutdown handled by lifespan above

# Include API routers for devices, commands, and configurations.
app.include_router(devices_router)
app.include_router(commands_router)
app.include_router(configurations_router)


@app.get("/{spa_path:path}", include_in_schema=False)
async def serve_spa_assets(spa_path: str, request: Request) -> Response:
    """Serve SPA assets or proxy; mirrors legacy behavior for tests."""
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
        # FileResponse takes a path; FastAPI will set .path attribute for tests
        from fastapi.responses import FileResponse as _FileResponse

        return _FileResponse(asset_path)
    if asset_path.is_dir():
        index_path = asset_path / "index.html"
        if index_path.is_file():
            from fastapi.responses import FileResponse as _FileResponse

            return _FileResponse(index_path)
    if "." in spa_path:
        raise HTTPException(status_code=404)
    primary_path = FRONTEND_DIST / PRIMARY_ENTRY
    if primary_path.exists():
        html_content = primary_path.read_text(encoding="utf-8")
        # Inject base tag for Ingress if X-Ingress-Path is present
        html_content = _inject_base_tag_if_needed(request, html_content)
        return HTMLResponse(html_content)
    legacy_path = FRONTEND_DIST / LEGACY_ENTRY
    if legacy_path.exists():
        html_content = legacy_path.read_text(encoding="utf-8")
        # Inject base tag for Ingress if X-Ingress-Path is present
        html_content = _inject_base_tag_if_needed(request, html_content)
        return HTMLResponse(html_content)
    raise HTTPException(status_code=404)



def main() -> None:  # pragma: no cover
    """Run the FastAPI service under Uvicorn for Home Assistant add-on.

    This function is called by the S6 service in the HA add-on container
    via 'python3 -m aquable.service'. Configuration is handled via
    environment variables set by the S6 service script.
    """
    import sys
    import os
    import logging
    import time
    import uvicorn

    # Configure logging with timezone support
    # The TZ environment variable is set by the run script
    # Note: Let uvicorn handle logging to avoid double output
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
    
    logger = logging.getLogger(__name__)
    tz = os.getenv("TZ", "UTC")
    
    # Determine port: Ingress uses 8099, standalone uses 8000
    # When running under Home Assistant Supervisor, SUPERVISOR_TOKEN is set
    is_ingress = bool(os.getenv("SUPERVISOR_TOKEN"))
    port = int(os.getenv("INGRESS_PORT", "8099" if is_ingress else "8000"))
    
    logger.info(f"Starting AquaBle with timezone: {tz}")
    logger.info(f"Ingress mode: {is_ingress}, listening on port: {port}")
    logger.info(f"App object: {app}")
    
    # Back-compat: export service instance for tests
    service = get_service()
    
    try:
        logger.info(f"Calling uvicorn.run() on port {port}...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        import traceback
        logger.error(f"FATAL ERROR: {e}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
