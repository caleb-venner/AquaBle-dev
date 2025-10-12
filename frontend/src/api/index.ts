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
  refreshDeviceStatus
} from "./devices";

// Configuration management
export {
  getDoserConfigurations,
  getDoserConfiguration,
  updateDoserConfiguration,
  deleteDoserConfiguration,
  getLightConfigurations,
  getLightConfiguration,
  updateLightConfiguration,
  deleteLightConfiguration,
  getConfigurationSummary,
  formatMacAddress,
  getShortDeviceName,
  isValidTimeFormat,
  sortAutoSettings,
  validateDoserConfig,
  validateLightProfile,
} from "./configurations";

export type {
  DoserHead,
  DoserDevice,
  LightChannel,
  AutoSetting,
  LightProfile,
  LightDevice,
  ConfigurationSummary,
} from "./configurations";
