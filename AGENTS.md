# AquaBle - AI Coding Guidelines

IMPORTANT: This file contains instructions for automated coding assistants and contributors. Please read before making edits.

- Do NOT generate or add user-facing documentation files (guides, HOWTOs, tutorials) unless explicitly requested by the project owner. The project maintainers prefer documentation to be created intentionally and reviewed before inclusion.

## Architecture Overview

**Standalone Web Application**: This project is a standalone web application that manages Chihiros aquarium devices (lights/dosers) over BLE via ESPHome Bluetooth Proxies. It consists of a lightweight FastAPI backend and a vanilla TypeScript/Vite frontend.

**Key Principles**:

- **Functional Paradigm**: Keep the backend functional, lightweight, and performant. Avoid OOP overhead bloat (e.g., deep class hierarchies, excessive state encapsulation).
- **Clear Separation of Concerns**: Functions should be concise and have a single, clear responsibility.
- **No Utils**: Do NOT create `utils.py` files or `utils/` directories. Code should be organised into specific, descriptive modules based on its domain or function.
- **Australian English**: Use Australian spelling (e.g., colour, organise, initialise, behaviour) throughout the codebase and comments.

**Key Components**:

- **Core APIs**: `api/` directory containing specific route files (e.g., `routes_devices.py`, `routes_commands.py`).
- **Core Logic**: `core/` directory handling BLE proxy orchestration, connection lifecycles, and dispatching.
- **Domain Models**: `domain/` directory containing structured dataclasses for device statuses (`LightStatus`, `DoserStatus`) and local JSON storage logic.
- **Commands**: `commands/` directory containing functional encoders and parsers for the Chihiros BLE protocol.
- **Frontend**: A highly dynamic, premium-feeling vanilla TypeScript frontend built with Vite and Zustand for state management.

**BLE Protocol**: Reverse-engineered Chihiros UART service (`6E400001-B5A3-F393-E0A9-E50E24DCCA9E`) with RX/TX characteristics. Commands sent as notifications, responses received via notifications. Command structure: `[Command ID, Length, Message ID High/Low, Mode, Parameters..., Checksum]` with XOR checksum.

## Developer Workflows

**Local Development**:

- Use `make dev` to start both the backend and frontend development servers concurrently.
- Use `make kill` to clean up zombie processes.
- The backend runs on `0.0.0.0:8000` and the frontend runs via Vite on port 5173.
- Relies on ESPHome Bluetooth Proxies for communication (`ESPHomeClient`).

## Project Conventions

**Device Command Encoding**:

- Commands use structured byte arrays: `[Command ID, Length, Message ID High/Low, Mode, Parameters..., Checksum]`
- Message IDs increment per session, skipping 0x5A (90) in both bytes via `encoder.next_message_id()`
- Checksum is XOR of all command bytes starting from the second byte.

**Functional Approach**:
Instead of `class BaseDevice`, we use standard functions that pass explicit state:

```python
async def execute_ble_commands(
    address: str, 
    payloads: list[bytearray], 
    wait_for_status: bool = False
) -> list[bytearray]:
    # Handles ESPHome proxy connection, payload transmission, and response collection
```

## Guidelines for AI Assistant

**Do NOT create summary documentation or improvement reports** unless explicitly requested by the user. Focus only on:

- Fixing bugs or issues raised
- Implementing features requested
- Code quality improvements when asked
- Explanations of what was changed (inline, not as documents)

If changes are significant and deserve documentation, ask the user first before creating any files.
