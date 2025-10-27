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
export async function connectDevice(address: string): Promise<DeviceStatus> {
  return postJson<DeviceStatus>(`api/devices/${encodeURIComponent(address)}/connect`, {});
}

/**
 * Disconnect from a specific device
 */
export async function disconnectDevice(address: string): Promise<void> {
  await postJson(`api/devices/${encodeURIComponent(address)}/disconnect`, {});
}

/**
 * Refresh status for a specific device
 */
export async function refreshDeviceStatus(address: string): Promise<void> {
  await postJson(`api/devices/${encodeURIComponent(address)}/status`, {});
}

/**
 * Scan for nearby supported devices
 */
export async function scanDevices(timeout: number = 5.0): Promise<ScanDevice[]> {
  return fetchJson<ScanDevice[]>(`api/scan?timeout=${timeout}`);
}
