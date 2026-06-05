"""JSONL based command history tracking."""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

CommandStatus = Literal["pending", "running", "success", "failed", "timed_out", "cancelled"]

@dataclass(slots=True)
class CommandRecord:
    """Persistent record of a command execution."""

    action: str
    address: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    args: dict[str, Any] | None = None
    status: CommandStatus = "pending"
    attempts: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "address": self.address,
            "action": self.action,
            "args": self.args,
            "status": self.status,
            "attempts": self.attempts,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def mark_started(self) -> None:
        self.status = "running"
        self.started_at = time.time()
        self.attempts += 1

    def mark_success(self, result: dict[str, Any] | None = None) -> None:
        self.status = "success"
        self.result = result
        self.completed_at = time.time()

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self.completed_at = time.time()


def append_command_log(config_dir: Path, record: CommandRecord) -> None:
    """Append a command record to the JSONL command history file."""
    log_file = config_dir / "command_history.jsonl"
    try:
        # Open in append mode
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")
    except OSError as e:
        logger.error(f"Failed to write to command log: {e}")

def read_command_history(config_dir: Path, address: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Read the recent command history from the JSONL file."""
    log_file = config_dir / "command_history.jsonl"
    if not log_file.exists():
        return []
        
    records = []
    try:
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if address is None or record.get("address") == address:
                        records.append(record)
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        logger.error(f"Failed to read command log: {e}")
        return []
        
    # Return most recent first
    return list(reversed(records))[-limit:]
