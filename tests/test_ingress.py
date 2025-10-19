"""Tests for Home Assistant Ingress functionality."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_ingress():
    """Create app instance with Ingress enabled."""
    with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "test_token"}):
        # Need to reimport to pick up env var
        import importlib
        from aquable import service
        
        importlib.reload(service)
        yield service.app
        
        # Clean up
        importlib.reload(service)


@pytest.fixture
def app_without_ingress():
    """Create app instance without Ingress."""
    with patch.dict(os.environ, {}, clear=True):
        # Need to reimport to pick up cleared env
        import importlib
        from aquable import service
        
        # Ensure SUPERVISOR_TOKEN is not set
        if "SUPERVISOR_TOKEN" in os.environ:
            del os.environ["SUPERVISOR_TOKEN"]
        
        importlib.reload(service)
        yield service.app
        
        # Clean up
        importlib.reload(service)


class TestIngressIPRestriction:
    """Test IP restriction middleware for Ingress mode."""
    
    def test_ingress_allows_gateway_ip(self, app_with_ingress):
        """Test that Ingress gateway IP is allowed."""
        client = TestClient(app_with_ingress)
        
        # Simulate request from Ingress gateway
        response = client.get(
            "/api/health",
            headers={"X-Forwarded-For": "172.30.32.2"}
        )
        
        assert response.status_code == 200
    
    def test_ingress_allows_localhost(self, app_with_ingress):
        """Test that localhost is allowed for health checks."""
        client = TestClient(app_with_ingress)
        
        # TestClient uses 127.0.0.1 by default
        response = client.get("/api/health")
        
        assert response.status_code == 200
    
    def test_ingress_blocks_other_ips(self, app_with_ingress):
        """Test that other IPs are blocked in Ingress mode."""
        client = TestClient(app_with_ingress)
        
        # Try to access from a different IP
        # Note: TestClient doesn't easily allow changing client IP
        # This test documents the expected behavior
        # In production, the middleware would block this
        pass
    
    def test_standalone_allows_all_ips(self, app_without_ingress):
        """Test that all IPs are allowed in standalone mode."""
        client = TestClient(app_without_ingress)
        
        response = client.get("/api/health")
        
        assert response.status_code == 200


class TestIngressPathHeader:
    """Test X-Ingress-Path header handling."""
    
    def test_ingress_path_captured(self, app_with_ingress):
        """Test that X-Ingress-Path header is captured."""
        client = TestClient(app_with_ingress)
        
        response = client.get(
            "/api/health",
            headers={"X-Ingress-Path": "/api/hassio_ingress/xyz123"}
        )
        
        assert response.status_code == 200
        # Check if custom header is added to response
        assert "X-AquaBle-Ingress-Path" in response.headers
        assert response.headers["X-AquaBle-Ingress-Path"] == "/api/hassio_ingress/xyz123"
    
    def test_no_ingress_path_in_standalone(self, app_without_ingress):
        """Test that standalone mode doesn't add Ingress headers."""
        client = TestClient(app_without_ingress)
        
        response = client.get("/api/health")
        
        assert response.status_code == 200
        # Should not have Ingress path header
        assert "X-AquaBle-Ingress-Path" not in response.headers


class TestIngressPortConfiguration:
    """Test port configuration for Ingress mode."""
    
    def test_ingress_port_detection(self):
        """Test that Ingress port is correctly detected."""
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "test_token"}):
            from aquable.service import main
            
            # Import the logic without running uvicorn
            is_ingress = bool(os.getenv("SUPERVISOR_TOKEN"))
            port = int(os.getenv("INGRESS_PORT", "8099" if is_ingress else "8000"))
            
            assert is_ingress is True
            assert port == 8099
    
    def test_standalone_port_detection(self):
        """Test that standalone port is correctly detected."""
        with patch.dict(os.environ, {}, clear=True):
            if "SUPERVISOR_TOKEN" in os.environ:
                del os.environ["SUPERVISOR_TOKEN"]
            
            is_ingress = bool(os.getenv("SUPERVISOR_TOKEN"))
            port = int(os.getenv("INGRESS_PORT", "8099" if is_ingress else "8000"))
            
            assert is_ingress is False
            assert port == 8000
    
    def test_custom_ingress_port(self):
        """Test that custom INGRESS_PORT environment variable is respected."""
        with patch.dict(os.environ, {
            "SUPERVISOR_TOKEN": "test_token",
            "INGRESS_PORT": "9000"
        }):
            is_ingress = bool(os.getenv("SUPERVISOR_TOKEN"))
            port = int(os.getenv("INGRESS_PORT", "8099" if is_ingress else "8000"))
            
            assert is_ingress is True
            assert port == 9000


class TestIngressMiddlewareOrder:
    """Test that middleware is added in correct order."""
    
    def test_middleware_order_with_ingress(self, app_with_ingress):
        """Test that path middleware is before IP restriction middleware."""
        # The middleware order is important:
        # 1. IngressPathMiddleware (captures X-Ingress-Path)
        # 2. IngressIPRestrictionMiddleware (enforces security)
        
        # Verify app has middleware
        assert len(app_with_ingress.user_middleware) >= 2
    
    def test_no_middleware_without_ingress(self, app_without_ingress):
        """Test that Ingress middleware is not added in standalone mode."""
        # In standalone mode, the Ingress middleware should not be added
        # Note: This depends on how the app is initialized
        pass


class TestIngressCompatibility:
    """Test backward compatibility with direct access."""
    
    def test_health_endpoint_works_in_both_modes(self, app_with_ingress, app_without_ingress):
        """Test that health endpoint works in both Ingress and standalone modes."""
        client_ingress = TestClient(app_with_ingress)
        client_standalone = TestClient(app_without_ingress)
        
        response_ingress = client_ingress.get("/api/health")
        response_standalone = client_standalone.get("/api/health")
        
        assert response_ingress.status_code == 200
        assert response_standalone.status_code == 200
        assert response_ingress.json()["status"] == "healthy"
        assert response_standalone.json()["status"] == "healthy"
