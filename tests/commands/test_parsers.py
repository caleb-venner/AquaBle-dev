"""Tests for BLE payload parsing functions."""

from src.aquable.commands.parsers import parse_doser_payload, parse_light_payload
from src.aquable.domain.doser.status import DoserStatus
from src.aquable.domain.light.status import LightStatus


def test_parse_doser_0xFE_payload():
    # 0xFE is daily head data + general state
    # Format: [0x5B, msg_high, msg_low, msg_high, msg_low, mode=0xFE, weekday, hour, minute]
    # Followed by 9 byte blocks per head.
    payload = bytearray([
        0x5B, 0x00, 0x00, 0x01, 0x02, 0xFE, 2, 10, 30,
    ])
    # Add one head block (9 bytes)
    # mode, hour, minute, extra[4], dosed_h, dosed_l
    payload.extend([0x01, 10, 30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1A]) # Dosed = 26
    
    # Add tail (5 bytes)
    payload.extend([0x00, 0x00, 0x00, 0x00, 0xFF])
    
    status = parse_doser_payload(payload)
    assert status is not None
    assert isinstance(status, DoserStatus)
    assert status.response_mode == 0xFE
    assert len(status.heads) == 1
    assert status.heads[0].dosed_tenths_ml == 26

def test_parse_doser_0x1E_payload():
    # 0x1E is lifetime totals
    payload = bytearray([0x5B, 0x00, 0x00, 0x01, 0x02, 0x1E])
    # 4 heads, 2 bytes each = 8 bytes
    payload.extend([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]) # Head 1: 256
    
    status = parse_doser_payload(payload)
    assert status is not None
    assert status.response_mode == 0x1E
    assert len(status.lifetime_totals_tenths_ml) == 4
    assert status.lifetime_totals_tenths_ml[0] == 256

def test_parse_doser_invalid():
    assert parse_doser_payload(b"short") is None
    assert parse_doser_payload(bytearray([0x5A] + [0]*31)) is None

def test_parse_light_payload():
    # Light expects 0xFE
    payload = bytearray([
        0x5B, 0x00, 0x00, 0x01, 0x02, 0xFE, 2, 10, 30
    ])
    # Add dummy keyframes: hour, minute, value (3 bytes)
    payload.extend([12, 30, 100])
    # Tail 5 bytes
    payload.extend([0x00, 0x00, 0x00, 0x00, 0x00])
    
    status = parse_light_payload(payload)
    assert status is not None
    assert isinstance(status, LightStatus)
    assert status.response_mode == 0xFE
    assert len(status.keyframes) == 1
    assert status.keyframes[0].value == 100
