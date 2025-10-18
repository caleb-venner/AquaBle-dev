"""FastAPI service module for Chihiros BLE devices.

This module keeps only the web-facing FastAPI wiring. The BLE orchestration
implementation (CachedStatus, BLEService and persistence helpers) has been
extracted to ``ble_service.py`` to improve modularity. We import the
implementation and expose the same public names for backwards compatibility.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

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

service = BLEService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage BLE service startup and shutdown via FastAPI lifespan."""
    # Make service instance available to routers
    app.state.service = service
    await service.start()
    try:
        yield
    finally:
        await service.stop()


app = FastAPI(title="Aquarium BLE Service", lifespan=lifespan)


# Health check endpoint for container monitoring
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker/HA monitoring."""
    try:
        # Basic service availability check
        cached_statuses = service.get_status_snapshot()
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


# Mount SPA assets via helper module
spa.mount_assets(app)


@app.get("/", response_class=HTMLResponse)
async def serve_spa() -> Response:
    """Serve SPA index or proxy to dev server; mirrors legacy behavior for tests."""
    # Use local constants to support monkeypatching in tests
    if SPA_DIST_AVAILABLE:
        primary_path = FRONTEND_DIST / PRIMARY_ENTRY
        if primary_path.exists():
            return HTMLResponse(primary_path.read_text(encoding="utf-8"))
        legacy_path = FRONTEND_DIST / LEGACY_ENTRY
        if legacy_path.exists():
            return HTMLResponse(legacy_path.read_text(encoding="utf-8"))
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
async def serve_spa_assets(spa_path: str) -> Response:
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
        return HTMLResponse(primary_path.read_text(encoding="utf-8"))
    legacy_path = FRONTEND_DIST / LEGACY_ENTRY
    if legacy_path.exists():
        return HTMLResponse(legacy_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404)



def main() -> None:  # pragma: no cover
    """Run the FastAPI service under Uvicorn for Home Assistant add-on.

    This function is called by the S6 service in the HA add-on container
    via 'python3 -m aquable.service'. Configuration is handled via
    environment variables set by the S6 service script.
    """
    import sys
    import uvicorn

    try:
        uvicorn.run(
            "aquable.service:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        import traceback
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

