"""Tests specifically for SPA serving and asset routing logic."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from aquable.service import SPA_UNAVAILABLE_MESSAGE, serve_spa, serve_spa_assets


def _make_mock_request():
    """Create a mock Request object for testing."""
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.state = MagicMock()
    mock_request.state.ingress_path = ""
    return mock_request


def test_root_reports_missing_spa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose a helpful 503 when neither SPA bundle nor dev server exist."""
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", False)
    monkeypatch.setattr(
        "aquable.service._proxy_dev_server",
        AsyncMock(return_value=None),
    )

    mock_request = _make_mock_request()
    response = asyncio.run(serve_spa(mock_request))
    assert response.status_code == 503
    # response.body can be a memoryview on some FastAPI/Starlette versions —
    # convert to bytes first before decoding to avoid `memoryview` attribute errors
    assert SPA_UNAVAILABLE_MESSAGE in bytes(response.body).decode()


def test_root_serves_spa_when_dist_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Return the compiled SPA index when the build directory exists."""
    index_file = tmp_path / "index.html"
    index_file.write_text("<html><body>spa</body></html>", encoding="utf-8")
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", True)
    monkeypatch.setattr("aquable.service.FRONTEND_DIST", tmp_path)

    mock_request = _make_mock_request()
    response = asyncio.run(serve_spa(mock_request))
    assert response.status_code == 200
    assert b"spa" in response.body


def test_spa_asset_route_serves_static_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Return static assets from the compiled SPA directory."""
    asset = tmp_path / "vite.svg"
    asset.write_text("svg", encoding="utf-8")
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", True)
    monkeypatch.setattr("aquable.service.FRONTEND_DIST", tmp_path)

    mock_request = _make_mock_request()
    response = asyncio.run(serve_spa_assets("vite.svg", mock_request))
    assert response.status_code == 200
    assert getattr(response, "path", None) == asset


def test_spa_asset_route_returns_index_for_client_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Serve the SPA index for non-file client-side routes."""
    index_file = tmp_path / "index.html"
    index_file.write_text("<html><body>spa</body></html>", encoding="utf-8")
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", True)
    monkeypatch.setattr("aquable.service.FRONTEND_DIST", tmp_path)

    mock_request = _make_mock_request()
    response = asyncio.run(serve_spa_assets("dashboard", mock_request))
    assert response.status_code == 200
    assert "spa" in bytes(response.body).decode()


def test_spa_asset_route_404_for_missing_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing assets should not fall back to the SPA index."""
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", True)
    monkeypatch.setattr("aquable.service.FRONTEND_DIST", tmp_path)

    mock_request = _make_mock_request()
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(serve_spa_assets("app.js", mock_request))

    assert excinfo.value.status_code == 404


def test_root_proxies_dev_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve the SPA from the dev server when no build artifacts exist."""
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", False)
    proxied = HTMLResponse("dev")
    helper = AsyncMock(return_value=proxied)
    monkeypatch.setattr("aquable.service._proxy_dev_server", helper)

    mock_request = _make_mock_request()
    response = asyncio.run(serve_spa(mock_request))
    assert response is proxied
    helper.assert_awaited_once_with("/modern.html")


def test_spa_asset_route_proxies_dev_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proxy SPA asset requests to the Vite dev server when available."""
    monkeypatch.setattr("aquable.service.SPA_DIST_AVAILABLE", False)
    proxied = HTMLResponse("console.log('dev')")
    helper = AsyncMock(return_value=proxied)
    monkeypatch.setattr("aquable.service._proxy_dev_server", helper)

    mock_request = _make_mock_request()
    response = asyncio.run(serve_spa_assets("src/main.ts", mock_request))
    assert response is proxied
    helper.assert_awaited_once_with("/src/main.ts")
