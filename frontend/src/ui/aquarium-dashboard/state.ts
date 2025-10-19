/**
 * Dashboard state management
 */

import type { DashboardState, DashboardTab, ConnectionStability } from "./types";
import type { DoserDevice, LightDevice, DeviceMetadata, LightMetadata, ConfigurationSummary } from "../../api/configurations";
import type { StatusResponse } from "../../types/models";

// Global dashboard state
let dashboardState: DashboardState = {
  currentTab: "overview",
  doserConfigs: [],
  lightConfigs: [],
  doserMetadata: [],
  lightMetadata: [],
  summary: null,
  deviceStatus: null,
  error: null,
  connectingDevices: new Set<string>(),
  connectionStability: {},
  isRefreshing: false,
  isDataLoaded: false,
};

/**
 * Get current dashboard state
 */
export function getDashboardState(): DashboardState {
  return { ...dashboardState };
}

/**
 * Update dashboard state
 */
export function updateDashboardState(updates: Partial<DashboardState>): void {
  dashboardState = { ...dashboardState, ...updates };
}

/**
 * Set current tab
 */
export function setCurrentTab(tab: DashboardTab): void {
  dashboardState.currentTab = tab;
}

/**
 * Set error state
 */
export function setError(error: string | null): void {
  dashboardState.error = error;
}

/**
 * Update doser configurations
 */
export function setDoserConfigs(configs: DoserDevice[]): void {
  dashboardState.doserConfigs = configs;
}

/**
 * Update light configurations
 */
export function setLightConfigs(configs: LightDevice[]): void {
  dashboardState.lightConfigs = configs;
}

/**
 * Update doser metadata
 */
export function setDoserMetadata(metadata: DeviceMetadata[]): void {
  dashboardState.doserMetadata = metadata;
}

/**
 * Update light metadata
 */
export function setLightMetadata(metadata: LightMetadata[]): void {
  dashboardState.lightMetadata = metadata;
}

/**
 * Update configuration summary
 */
export function setSummary(summary: ConfigurationSummary | null): void {
  dashboardState.summary = summary;
}

/**
 * Update device status
 */
export function setDeviceStatus(status: StatusResponse | null): void {
  dashboardState.deviceStatus = status;
}

/**
 * Add device to connecting state
 */
export function addConnectingDevice(address: string): void {
  dashboardState.connectingDevices.add(address);
}

/**
 * Remove device from connecting state
 */
export function removeConnectingDevice(address: string): void {
  dashboardState.connectingDevices.delete(address);
}

/**
 * Check if device is currently connecting
 */
export function isDeviceConnecting(address: string): boolean {
  return dashboardState.connectingDevices.has(address);
}

/**
 * Update connection stability for a device
 */
export function updateConnectionStability(address: string, updates: Partial<ConnectionStability>): void {
  const current = dashboardState.connectionStability[address] || {
    isStable: true,
    reconnectAttempts: 0,
    consecutiveFailures: 0
  };

  dashboardState.connectionStability[address] = {
    ...current,
    ...updates
  };
}

/**
 * Mark device as having connection issues
 */
export function markDeviceUnstable(address: string): void {
  updateConnectionStability(address, {
    isStable: false,
    lastDisconnectTime: Date.now(),
    consecutiveFailures: (dashboardState.connectionStability[address]?.consecutiveFailures || 0) + 1
  });
}

/**
 * Mark device as having stable connection
 */
export function markDeviceStable(address: string): void {
  updateConnectionStability(address, {
    isStable: true,
    consecutiveFailures: 0,
    lastSuccessfulCommand: Date.now()
  });
}

/**
 * Get connection stability for a device
 */
export function getConnectionStability(address: string): ConnectionStability {
  return dashboardState.connectionStability[address] || {
    isStable: true,
    reconnectAttempts: 0,
    consecutiveFailures: 0
  };
}

/**
 * Set refreshing state
 */
export function setRefreshing(refreshing: boolean): void {
  dashboardState.isRefreshing = refreshing;
}

/**
 * Set data loaded state
 */
export function setDataLoaded(loaded: boolean): void {
  dashboardState.isDataLoaded = loaded;
}
