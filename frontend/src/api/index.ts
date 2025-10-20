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
  getLiveStatus,
  connectDevice,
  disconnectDevice,
  refreshDeviceStatus,
  scanDevices,
} from "./devices";

// Configuration management
export {
  // Doser configuration functions
  getDoserConfigurations,
  getDoserConfiguration,
  updateDoserConfiguration,
  deleteDoserConfiguration,
  // Light configuration functions
  getLightConfigurations,
  getLightConfiguration,
  updateLightConfiguration,
  deleteLightConfiguration,
  // Configuration summary
  getConfigurationSummary,
  // Helper functions
  formatMacAddress,
  getShortDeviceName,
  isValidTimeFormat,
  sortAutoSettings,
  validateDoserConfig,
  validateLightProfile,
  // System configuration
  getSystemTimezone,
  // Metadata functions
  updateDoserMetadata,
  getDoserMetadata,
  listDoserMetadata,
  updateLightMetadata,
  getLightMetadata,
  listLightMetadata,
} from "./configurations";

// Configuration types
export type {
  DoserHead,
  DoserDevice,
  LightChannel,
  AutoSetting,
  LightProfile,
  LightDevice,
  ConfigurationSummary,
  SystemTimezone,
  DeviceMetadata,
  LightMetadata,
} from "./configurations";
