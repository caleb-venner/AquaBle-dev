"""Tests for the functional dispatcher orchestration."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.aquable.core.dispatcher import set_doser_schedule


@pytest.mark.asyncio
async def test_set_doser_schedule_integration(tmp_path: Path):
    # Mock the ble_client so we don't actually try to connect to bluetooth
    with patch("src.aquable.core.ble_client.execute_ble_commands", new_callable=AsyncMock) as mock_ble:
        
        # Mock returning a successful 0xFE payload
        mock_ble.return_value = [
            bytearray([
                0x5B, 0x00, 0x00, 0x01, 0x02, 0xFE, 2, 10, 30,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0A,
                0x00, 0x00, 0x00, 0x00, 0xFF
            ])
        ]
        
        new_msg_id, final_status = await set_doser_schedule(
            config_dir=tmp_path,
            device_id="AA:BB:CC",
            msg_id=(1, 2),
            head_index=1,
            volume_tenths_ml=10,
            hour=8,
            minute=0,
            weekdays=["monday"]
        )
        
        # Verify ble_client was called once with the correct payloads
        mock_ble.assert_called_once()
        kwargs = mock_ble.call_args.kwargs
        assert kwargs["address"] == "AA:BB:CC"
        assert kwargs["wait_for_status"] is True
        assert len(kwargs["payloads"]) > 0
        
        # Verify the dispatcher successfully parsed the mocked return bytes
        assert final_status is not None
        assert final_status.response_mode == 0xFE
        assert final_status.heads[0].dosed_tenths_ml == 10
