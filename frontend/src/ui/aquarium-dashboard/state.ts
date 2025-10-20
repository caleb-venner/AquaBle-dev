/**
 * Dashboard state management (LEGACY ADAPTER)
 * 
 * This file now acts as a thin adapter layer that delegates to the Zustand store.
 * All state is managed by stores/deviceStore.ts - this file exists only for
 * backwards compatibility with components that haven't been migrated yet.
 * 
 * TODO: Migrate remaining components to use deviceStore directly and remove this file.
 */

import { deviceStore } from "../../stores/deviceStore";
import type { DashboardState, DashboardTab, ConnectionStability } from "./types";
import type { DoserDevice, LightDevice, DeviceMetadata, LightMetadata, ConfigurationSummary } from "../../api/configurations";
import type { StatusResponse } from "../../types/models";

/**
 * Get current dashboard state (delegates to Zustand store)
 */
export function getDashboardState(): DashboardState {
  const state = deviceStore.getState();
  
  // Convert Zustand state to legacy DashboardState format
  const deviceStatus: { [address: string]: any } = {};
  state.devices.forEach((device, address) => {
    if (device.status) {
      deviceStatus[address] = device.status;
    }
  });

  const doserConfigs = Array.from(state.configurations.dosers.values());
  const lightConfigs = Array.from(state.configurations.lights.values());

  // Extract metadata from configurations
  const doserMetadata: DeviceMetadata[] = doserConfigs.map(config => ({
    id: config.id,
    name: config.name,
    autoReconnect: true,
    createdAt: config.createdAt,
    updatedAt: config.updatedAt,
  }));

  const lightMetadata: LightMetadata[] = lightConfigs.map(config => ({
    id: config.id,
    name: config.name,
    autoReconnect: true,
    createdAt: config.createdAt,
    updatedAt: config.updatedAt,
  }));

  return {
    currentTab: state.ui.currentView as DashboardTab,
    doserConfigs,
    lightConfigs,
    doserMetadata,
    lightMetadata,
    summary: null, // TODO: Load from API if needed
    deviceStatus: Object.keys(deviceStatus).length > 0 ? deviceStatus : null,
    error: state.ui.globalError,
    connectingDevices: new Set(
      Array.from(state.devices.values())
        .filter(d => d.isLoading)
        .map(d => d.address)
    ),
    connectionStability: {}, // TODO: Implement if needed
    isRefreshing: Array.from(state.devices.values()).some(d => d.isLoading),
    isDataLoaded: state.configurations.isLoaded && state.devices.size > 0,
  };
}

/**
 * Update dashboard state (NO-OP: Use Zustand store directly)
 * @deprecated Use deviceStore.getState().actions instead
 */
export function updateDashboardState(updates: Partial<DashboardState>): void {
  console.warn('updateDashboardState is deprecated. Use deviceStore actions instead.');
  // Legacy adapter - updates are handled by Zustand now
}

/**
 * Set current tab (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.setCurrentView instead
 */
export function setCurrentTab(tab: DashboardTab): void {
  deviceStore.getState().actions.setCurrentView(tab as any);
}

/**
 * Set error state (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.setGlobalError instead
 */
export function setError(error: string | null): void {
  deviceStore.getState().actions.setGlobalError(error);
}

/**
 * Update doser configurations (delegates to Zustand)
 * @deprecated Configurations are loaded automatically by deviceStore
 */
export function setDoserConfigs(configs: DoserDevice[]): void {
  console.warn('setDoserConfigs is deprecated. Configurations are managed by deviceStore.');
  // Managed by Zustand now
}

/**
 * Update light configurations (delegates to Zustand)
 * @deprecated Configurations are loaded automatically by deviceStore
 */
export function setLightConfigs(configs: LightDevice[]): void {
  console.warn('setLightConfigs is deprecated. Configurations are managed by deviceStore.');
  // Managed by Zustand now
}

/**
 * Update doser metadata (delegates to Zustand)
 * @deprecated Metadata is loaded with configurations in deviceStore
 */
export function setDoserMetadata(metadata: DeviceMetadata[]): void {
  console.warn('setDoserMetadata is deprecated. Metadata is managed by deviceStore.');
  // Managed by Zustand now
}

/**
 * Update light metadata (delegates to Zustand)
 * @deprecated Metadata is loaded with configurations in deviceStore
 */
export function setLightMetadata(metadata: LightMetadata[]): void {
  console.warn('setLightMetadata is deprecated. Metadata is managed by deviceStore.');
  // Managed by Zustand now
}

/**
 * Update configuration summary (delegates to Zustand)
 * @deprecated Use API directly if needed
 */
export function setSummary(summary: ConfigurationSummary | null): void {
  console.warn('setSummary is deprecated.');
  // Not currently used
}

/**
 * Update device status (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.updateDevice instead
 */
export function setDeviceStatus(status: StatusResponse | null): void {
  if (status) {
    Object.entries(status).forEach(([address, cachedStatus]) => {
      deviceStore.getState().actions.updateDevice(address, cachedStatus);
    });
  }
}

/**
 * Add device to connecting state (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.setDeviceLoading instead
 */
export function addConnectingDevice(address: string): void {
  deviceStore.getState().actions.setDeviceLoading(address, true);
}

/**
 * Remove device from connecting state (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.setDeviceLoading instead
 */
export function removeConnectingDevice(address: string): void {
  deviceStore.getState().actions.setDeviceLoading(address, false);
}

/**
 * Check if device is currently connecting (delegates to Zustand)
 * @deprecated Check device.isLoading in deviceStore instead
 */
export function isDeviceConnecting(address: string): boolean {
  const device = deviceStore.getState().devices.get(address);
  return device?.isLoading || false;
}

/**
 * Update connection stability for a device
 * @deprecated Connection stability tracking not fully implemented in Zustand yet
 */
export function updateConnectionStability(address: string, updates: Partial<ConnectionStability>): void {
  console.warn('updateConnectionStability is deprecated. Use device error states in Zustand.');
  // TODO: Implement if connection stability tracking is needed
}

/**
 * Mark device as having connection issues (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.setDeviceError instead
 */
export function markDeviceUnstable(address: string): void {
  deviceStore.getState().actions.setDeviceError(address, 'Connection unstable');
}

/**
 * Mark device as having stable connection (delegates to Zustand)
 * @deprecated Use deviceStore.getState().actions.setDeviceError instead
 */
export function markDeviceStable(address: string): void {
  deviceStore.getState().actions.setDeviceError(address, null);
}

/**
 * Get connection stability for a device
 * @deprecated Use device.error in deviceStore instead
 */
export function getConnectionStability(address: string): ConnectionStability {
  const device = deviceStore.getState().devices.get(address);
  return {
    isStable: !device?.error,
    reconnectAttempts: 0,
    consecutiveFailures: device?.error ? 1 : 0,
  };
}

/**
 * Set refreshing state (delegates to Zustand)
 * @deprecated Check device.isLoading states in deviceStore instead
 */
export function setRefreshing(refreshing: boolean): void {
  console.warn('setRefreshing is deprecated. Individual device loading states are managed by deviceStore.');
  // Managed by per-device loading states in Zustand
}

/**
 * Set data loaded state (delegates to Zustand)
 * @deprecated Check deviceStore.configurations.isLoaded instead
 */
export function setDataLoaded(loaded: boolean): void {
  console.warn('setDataLoaded is deprecated. Check deviceStore.configurations.isLoaded instead.');
  // Managed by Zustand configurations state
}
