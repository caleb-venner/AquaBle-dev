/**
 * Dashboard-specific type definitions
 */

import type { DoserDevice, LightDevice, DeviceMetadata, LightMetadata, ConfigurationSummary } from "../../api/configurations";
import type { StatusResponse } from "../../types/api";

export type DashboardTab = "overview" | "dev";

export interface ConnectionStability {
  isStable: boolean;
  lastDisconnectTime?: number;
  reconnectAttempts: number;
  consecutiveFailures: number;
  lastSuccessfulCommand?: number;
}

export interface DashboardState {
  currentTab: DashboardTab;
  doserConfigs: DoserDevice[];
  lightConfigs: LightDevice[];
  doserMetadata: DeviceMetadata[];
  lightMetadata: LightMetadata[];
  summary: ConfigurationSummary | null;
  deviceStatus: StatusResponse | null;
  error: string | null;
  connectingDevices: Set<string>; // Track devices currently being connected
  connectionStability: Record<string, ConnectionStability>; // Track connection health per device
  isRefreshing: boolean; // Track refresh all state
  isDataLoaded: boolean; // Track if initial data loading is complete
}

export interface DashboardHandlers {
  switchTab: (tab: DashboardTab) => Promise<void>;
  handleRefreshAll: () => Promise<void>;
  handleConnectDevice: (address: string) => Promise<void>;
  clearScanResults: () => void;
  handleConfigureDevice: (address: string, deviceType: string) => Promise<void>;
  handleDeviceSettings: (address: string, deviceType: string) => Promise<void>;
  handleDeleteDevice: (address: string, deviceType: string) => Promise<void>;
  handleConfigureDoser: (deviceId: string) => Promise<void>;
  handleConfigureLight: (deviceId: string) => Promise<void>;
  handleDeleteDoser: (deviceId: string) => Promise<void>;
  handleDeleteLight: (deviceId: string) => Promise<void>;
}
