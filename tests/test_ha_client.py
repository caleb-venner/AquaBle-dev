"""
Tests for Home Assistant API client
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from aquable.api.ha_client import HAClient, get_ha_client


@pytest.fixture
def mock_supervisor_token():
    """Mock SUPERVISOR_TOKEN environment variable"""
    with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "test-token-123"}):
        yield "test-token-123"


@pytest.fixture
def mock_no_token():
    """Mock absence of SUPERVISOR_TOKEN"""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def ha_client(mock_supervisor_token):
    """Create HA client instance with mocked token"""
    return HAClient()


@pytest.fixture
def ha_client_no_token(mock_no_token):
    """Create HA client instance without token"""
    return HAClient()


class TestHAClientAvailability:
    """Test HA client availability checks"""

    def test_is_available_with_token(self, ha_client):
        """Client should be available when token is present"""
        assert ha_client.is_available is True

    def test_is_available_without_token(self, ha_client_no_token):
        """Client should not be available without token"""
        assert ha_client_no_token.is_available is False


class TestHAClientGetState:
    """Test get_state method"""

    @pytest.mark.asyncio
    async def test_get_state_success(self, ha_client):
        """Should successfully retrieve entity state"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "state": "on",
            "attributes": {"friendly_name": "Test Switch"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(ha_client, '_get_client', return_value=AsyncMock()) as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await ha_client.get_state("switch.test")
            
            assert result is not None
            assert result["state"] == "on"
            assert result["attributes"]["friendly_name"] == "Test Switch"

    @pytest.mark.asyncio
    async def test_get_state_not_found(self, ha_client):
        """Should return None when entity not found"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)

        with patch.object(ha_client, '_get_client', return_value=AsyncMock()) as mock_client:
            mock_client.return_value.get = AsyncMock(side_effect=error)
            
            result = await ha_client.get_state("switch.nonexistent")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_state_without_token(self, ha_client_no_token):
        """Should return None when token not available"""
        result = await ha_client_no_token.get_state("switch.test")
        assert result is None


class TestHAClientToggleSwitch:
    """Test toggle_switch method"""

    @pytest.mark.asyncio
    async def test_toggle_switch_success(self, ha_client):
        """Should successfully toggle switch"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(ha_client, '_get_client', return_value=AsyncMock()) as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await ha_client.toggle_switch("switch.test")
            
            assert result is True

    @pytest.mark.asyncio
    async def test_toggle_switch_invalid_entity(self, ha_client):
        """Should fail for non-switch entity"""
        result = await ha_client.toggle_switch("light.test")
        assert result is False

    @pytest.mark.asyncio
    async def test_toggle_switch_without_token(self, ha_client_no_token):
        """Should fail when token not available"""
        result = await ha_client_no_token.toggle_switch("switch.test")
        assert result is False


class TestHAClientExecuteScript:
    """Test execute_script method"""

    @pytest.mark.asyncio
    async def test_execute_script_success(self, ha_client):
        """Should successfully execute script"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(ha_client, '_get_client', return_value=AsyncMock()) as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await ha_client.execute_script("script.test_routine")
            
            assert result is True

    @pytest.mark.asyncio
    async def test_execute_script_invalid_entity(self, ha_client):
        """Should fail for non-script entity"""
        result = await ha_client.execute_script("switch.test")
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_script_without_token(self, ha_client_no_token):
        """Should fail when token not available"""
        result = await ha_client_no_token.execute_script("script.test")
        assert result is False


def test_get_ha_client_singleton():
    """Should return same instance on repeated calls"""
    client1 = get_ha_client()
    client2 = get_ha_client()
    assert client1 is client2
