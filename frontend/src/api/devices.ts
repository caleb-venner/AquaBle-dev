// Device management API functions

import { fetchJson, postJson } from "./http";
import type {
  DeviceStatus,
  StatusResponse,
  ScanDevice
} from "../types/api";

/**
 * Get cached status for all devices
 */
export async function getDeviceStatus(): Promise<StatusResponse> {
  return fetchJson<StatusResponse>("api/status");
}

/**
 * Connect to a specific device and return its updated status
 */
export async function connectDevice(address: string, deviceType: string = 'light'): Promise<DeviceStatus> {
  return postJson<DeviceStatus>(`api/devices/${encodeURIComponent(address)}/connect?device_type=${encodeURIComponent(deviceType)}`, {});
}

/**
 * Disconnect from a specific device
 */
export async function disconnectDevice(address: string): Promise<void> {
  // Backend doesn't explicitly need disconnect right now, but just in case
  await postJson(`api/devices/${encodeURIComponent(address)}/disconnect`, {}).catch(() => {});
}

/**
 * Refresh status for a specific device
 */
export async function refreshDeviceStatus(address: string, deviceType: string = 'light'): Promise<void> {
  await postJson(`api/devices/${encodeURIComponent(address)}/status?device_type=${encodeURIComponent(deviceType)}`, {});
}

/**
 * Scan for nearby supported devices
 */
export async function scanDevices(timeout: number = 5.0): Promise<ScanDevice[]> {
  return fetchJson<ScanDevice[]>(`api/scan?timeout=${timeout}`);
}
