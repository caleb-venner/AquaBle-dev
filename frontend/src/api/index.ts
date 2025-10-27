// Consolidated API module - exports all API functions

// HTTP utilities
export { fetchJson, postJson, putJson, deleteJson } from "./http";

// Command system
export {
  executeCommand,
  getCommandHistory,
  getCommand,
} from "./commands";

// Device management
export {
  getDeviceStatus,
  connectDevice,
  disconnectDevice,
  refreshDeviceStatus,
  scanDevices,
} from "./devices";

// Configuration management
export {
  getDeviceConfiguration,
  updateDeviceConfiguration,
  updateDeviceNaming,
  updateDeviceSettings,
  exportDeviceConfiguration,
  importDeviceConfiguration,
} from "./configurations";

// Configuration types
export type {
  DoserHead,
  DoserDevice,
  LightChannel,
  AutoSetting,
  LightProfile,
  LightDevice,
  DeviceNamingUpdate,
  DeviceSettingsUpdate,
} from "./configurations";
