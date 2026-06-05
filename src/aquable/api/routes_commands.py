"""Unified command system API routes."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..core import dispatcher
from ..domain.command_log import CommandRecord, append_command_log, read_command_history

router = APIRouter(prefix="/api", tags=["commands"])

class CommandRequestSchema(BaseModel):
    action: str
    id: str | None = None
    args: dict[str, Any] | None = None
    timeout: float | None = None

def get_config_dir(request: Request) -> Path:
    """Helper to extract config directory from FastAPI state."""
    # This will be injected by our new main.py
    return request.app.state.config_dir

@router.post("/devices/{address}/commands")
async def execute_command(
    request: Request, address: str, command_request: CommandRequestSchema
) -> dict[str, Any]:
    """Execute a command on a device and return the result."""
    config_dir = get_config_dir(request)
    
    record = CommandRecord(
        id=command_request.id or "",
        address=address,
        action=command_request.action,
        args=command_request.args
    )
    record.mark_started()
    
    try:
        # Dummy message ID for now. Production can read last known msg_id from storage
        msg_id = (0, 0)
        result_status = None
        args = command_request.args or {}
        
        if command_request.action == "doser_set_daily_dose":
            new_msg_id, result_status = await dispatcher.set_doser_schedule(
                config_dir=config_dir,
                device_id=address,
                msg_id=msg_id,
                head_index=args.get("head_index", 1),
                volume_tenths_ml=args.get("volume_tenths_ml", 0),
                hour=args.get("hour", 0),
                minute=args.get("minute", 0),
                weekdays=args.get("weekdays")
            )
        elif command_request.action == "light_set_brightness":
            new_msg_id, result_status = await dispatcher.set_light_brightness(
                config_dir=config_dir,
                device_id=address,
                msg_id=msg_id,
                colors=args.get("colors", {})
            )
        else:
            raise ValueError(f"Unknown action: {command_request.action}")

        import dataclasses
        record.mark_success(dataclasses.asdict(result_status) if result_status else {})
        
    except Exception as exc:
        record.mark_failed(f"Command execution failed: {exc}")
        
    finally:
        append_command_log(config_dir, record)
        
    if record.status == "failed":
        raise HTTPException(status_code=500, detail=record.error)
        
    return record.to_dict()


@router.get("/devices/{address}/commands")
async def list_commands(request: Request, address: str, limit: int = 20) -> list[dict[str, Any]]:
    """List recent commands for a device."""
    config_dir = get_config_dir(request)
    return read_command_history(config_dir, address=address, limit=limit)
