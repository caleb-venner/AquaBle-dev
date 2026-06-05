#!/usr/bin/env python3
"""CLI tool for discovering and interacting with Chihiros devices.

Uses the same ESPHome proxy as the main application.
"""

import argparse
import asyncio
import json
import logging
import shlex
import sys
from pathlib import Path

from aquable.core.config import get_config_dir
from aquable.esphome_proxy import ESPHomeProxyManager, set_proxy_manager

logger = logging.getLogger("aquable.cli")

async def init_proxy() -> ESPHomeProxyManager | None:
    config_dir = get_config_dir()
    proxy_config_path = config_dir / "proxy.json"
    
    if not proxy_config_path.exists():
        print(f"Error: No proxy configuration found at {proxy_config_path}")
        return None
        
    with open(proxy_config_path, encoding="utf-8") as f:
        proxy_conf = json.load(f)
        
    host = proxy_conf.get("host")
    if not host:
        print("Error: No host found in proxy.json")
        return None
        
    proxy_manager = ESPHomeProxyManager(
        host=host,
        password=proxy_conf.get("password", ""),
        noise_psk=proxy_conf.get("noise_psk", "")
    )
    
    print(f"Connecting to ESPHome proxy at {host}...")
    await proxy_manager.start()
    set_proxy_manager(proxy_manager)
    
    # Wait for initial connection and scan
    await asyncio.sleep(2.0)
    return proxy_manager

async def cmd_scan(timeout: float = 5.0) -> None:
    """Discover devices via proxy."""
    from aquable.core.discovery import scan_devices
    print(f"Scanning for devices (timeout: {timeout}s)...")
    devices = await scan_devices(timeout=timeout)
    
    if not devices:
        print("No devices found.")
        return
        
    print(f"\nFound {len(devices)} device(s):")
    for addr, info in devices.items():
        print(f"  {addr} - {info.get('name', 'Unknown')} ({info.get('device_type', 'unknown')})")

async def cmd_status(address: str, device_type: str) -> None:
    """Get status payloads for a device."""
    from aquable.core.config import get_config_dir
    from aquable.core.dispatcher import request_status_and_update
    
    config_dir = get_config_dir()
    print(f"Requesting status for {address} ({device_type})...")
    
    try:
        msg_id, status = await request_status_and_update(
            config_dir=config_dir,
            device_id=address,
            device_type=device_type,
            msg_id=(0, 0)
        )
        
        if status:
            print(f"\nSuccess! Status parsed:")
            import dataclasses
            print(json.dumps(dataclasses.asdict(status), default=lambda o: o.hex() if isinstance(o, (bytes, bytearray)) else str(o), indent=2))
        else:
            print("\nFailed to get status.")
    except Exception as e:
        print(f"Error requesting status: {e}")

async def cmd_raw(address: str, payloads: list[str], timeout: float = 2.5) -> None:
    """Send raw hex payload to a device and print responses."""
    from aquable.core.ble_client import execute_ble_commands
    
    print(f"Sending raw payload to {address}...")
    try:
        hex_payloads = [bytearray.fromhex(p) for p in payloads]
    except ValueError as e:
        print(f"Invalid hex payload: {e}")
        return
        
    try:
        packets = await execute_ble_commands(
            address=address,
            payloads=hex_payloads,
            wait_for_status=True,
            timeout_seconds=timeout
        )
        
        print(f"\nReceived {len(packets)} response(s):")
        for i, p in enumerate(packets, 1):
            print(f"  {i}: {p.hex()}")
    except Exception as e:
        print(f"Error executing raw command: {e}")

async def interactive_loop() -> None:
    """Run the interactive shell."""
    print("\n--- AquaBle Interactive CLI ---")
    print("Commands:")
    print("  scan [timeout]")
    print("  status <address> <type: light|doser>")
    print("  raw <address> <hex_payload> [timeout]")
    print("  exit / quit")
    print("-------------------------------\n")
    
    while True:
        try:
            line = await asyncio.to_thread(input, "AquaBle> ")
            line = line.strip()
            if not line:
                continue
                
            parts = shlex.split(line)
            cmd = parts[0].lower()
            
            if cmd in ("exit", "quit"):
                break
                
            elif cmd == "scan":
                timeout = float(parts[1]) if len(parts) > 1 else 5.0
                await cmd_scan(timeout)
                
            elif cmd == "status":
                if len(parts) < 3:
                    print("Usage: status <address> <type>")
                    continue
                await cmd_status(parts[1], parts[2])
                
            elif cmd == "raw":
                if len(parts) < 3:
                    print("Usage: raw <address> <hex_payload> [timeout]")
                    continue
                address = parts[1]
                payloads = [parts[2]]
                timeout = float(parts[3]) if len(parts) > 3 else 2.5
                await cmd_raw(address, payloads, timeout)
                
            else:
                print(f"Unknown command: {cmd}")
                
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            print(f"Error processing command: {e}")

async def main() -> None:
    parser = argparse.ArgumentParser(description="AquaBle CLI Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    proxy = await init_proxy()
    if not proxy:
        return
        
    try:
        await interactive_loop()
    finally:
        print("\nShutting down proxy connection...")
        await proxy.stop()

if __name__ == "__main__":
    asyncio.run(main())
