// API client for device configuration management (unified endpoints only)

import { fetchJson, putJson, patchJson } from "./http";

// ============================================================================
// Type Definitions
// ============================================================================

// Doser Types
export interface DoserHead {
  index: number;
  active: boolean;
  schedule: any;
  recurrence: any;
  missedDoseCompensation: boolean;
  calibration: any;
}

export interface DoserParsedHead {
  mode: number;
  mode_label: string;
  hour: number;
  minute: number;
  dosed_tenths_ml: number;
  extra: string; // hex string
}

export interface DoserParsedStatus {
  response_mode: string; // First 3 bytes of payload as hex (e.g., "5B0630")
  message_id: [number, number] | null;
  weekday: number | null;
  hour: number | null;
  minute: number | null;
  heads: DoserParsedHead[];
  tail_targets: number[];
  tail_raw: string; // hex string
  tail_flag: number | null;
  lifetime_totals_tenths_ml?: number[];
}

export interface DoserLastStatus {
  model_name?: string;
  raw_payload?: string;
  parsed?: DoserParsedStatus;
  updated_at?: number;
}

export interface DoserDevice {
  id: string;
  name?: string;
  headNames?: Record<number, string>;
  configurations: any[];
  activeConfigurationId?: string;
  autoReconnect?: boolean;
  createdAt?: string;
  updatedAt?: string;
  last_status?: DoserLastStatus; // Optional live device status
}

// Light Types
export interface LightChannel {
  index?: number;        // Channel index (0, 1, 2, 3) - from status endpoint
  key: string;           // Channel index as string ("0", "1", "2", "3")
  label: string;         // Human-readable name ("Red", "Green", "Blue", "White")
  min?: number;          // Minimum value (default: 0)
  max?: number;          // Maximum value (default: 100)
  step?: number;         // Step increment (default: 1)
}

export interface AutoSetting {
  time: string;
  brightness: number;
}

export interface LightProfile {
  mode: "manual" | "custom" | "auto";
  levels?: Record<string, number>;
  points?: any[];
  programs?: any[];
}

export interface LightParsedStatus {
  response_mode: string; // First 3 bytes of payload as hex (e.g., "5B0630")
  message_id: [number, number] | null;
  weekday: number | null;
  hour: number | null;
  minute: number | null;
  keyframes: Array<{
    hour: number;
    minute: number;
    value: number;
    percent: number; // computed percentage (0-100)
  }>;
  time_markers: Array<[number, number]>;
  tail: string; // hex string
}

export interface LightLastStatus {
  model_name?: string;
  raw_payload?: string;
  parsed?: LightParsedStatus;
  updated_at?: number;
}

export interface LightDevice {
  id: string;
  name?: string;
  channels: LightChannel[];
  configurations: any[];
  activeConfigurationId?: string;
  autoReconnect?: boolean;
  createdAt?: string;
  updatedAt?: string;
  last_status?: LightLastStatus; // Optional live device status
}

// ============================================================================
// Unified Configuration API
// ============================================================================

export interface DeviceNamingUpdate {
  name?: string;
  headNames?: Record<number, string>;
}

export interface DeviceSettingsUpdate {
  configurations?: any[];
  activeConfigurationId?: string;
  autoReconnect?: boolean;
}

export async function getDeviceConfiguration(address: string): Promise<DoserDevice | LightDevice> {
  return fetchJson<DoserDevice | LightDevice>(
    `api/devices/${encodeURIComponent(address)}/configurations`
  );
}

export async function updateDeviceConfiguration(
  address: string,
  config: DoserDevice | LightDevice
): Promise<DoserDevice | LightDevice> {
  return putJson<DoserDevice | LightDevice>(
    `api/devices/${encodeURIComponent(address)}/configurations`,
    config
  );
}

export async function updateDeviceNaming(
  address: string,
  naming: DeviceNamingUpdate
): Promise<DoserDevice | LightDevice> {
  return patchJson<DoserDevice | LightDevice>(
    `api/devices/${encodeURIComponent(address)}/configurations/naming`,
    naming
  );
}

export async function updateDeviceSettings(
  address: string,
  settings: DeviceSettingsUpdate
): Promise<DoserDevice | LightDevice> {
  return patchJson<DoserDevice | LightDevice>(
    `api/devices/${encodeURIComponent(address)}/configurations/settings`,
    settings
  );
}

// ============================================================================
// Import/Export Functions
// ============================================================================

export async function exportDeviceConfiguration(
  address: string
): Promise<DoserDevice | LightDevice> {
  return fetchJson<DoserDevice | LightDevice>(
    `api/devices/${encodeURIComponent(address)}/configurations/export`
  );
}

export async function importDeviceConfiguration(
  address: string,
  file: File
): Promise<DoserDevice | LightDevice> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `api/devices/${encodeURIComponent(address)}/configurations/import`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Import failed");
  }

  return response.json();
}

// ============================================================================
// Helper Functions
// ============================================================================

export function formatMacAddress(address: string): string {
  return address.toUpperCase();
}

export function getShortDeviceName(address: string): string {
  return address.slice(-5).replace(":", "").toUpperCase();
}

export function isValidTimeFormat(time: string): boolean {
  const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
  return timeRegex.test(time);
}

export function sortAutoSettings(settings: AutoSetting[]): AutoSetting[] {
  return [...settings].sort((a, b) => {
    const [aHour, aMin] = a.time.split(":").map(Number);
    const [bHour, bMin] = b.time.split(":").map(Number);
    return aHour * 60 + aMin - (bHour * 60 + bMin);
  });
}

export function validateDoserConfig(config: DoserDevice): string[] {
  const errors: string[] = [];
  if (!config.id) {
    errors.push("Device ID is required");
  }
  if (!config.configurations || config.configurations.length === 0) {
    errors.push("At least one configuration must be present");
  }
  return errors;
}

export function validateLightProfile(config: LightDevice): string[] {
  const errors: string[] = [];
  if (!config.id) {
    errors.push("Device ID is required");
  }
  if (!config.channels || config.channels.length === 0) {
    errors.push("At least one channel must be defined");
  }
  if (!config.configurations || config.configurations.length === 0) {
    errors.push("At least one configuration must be present");
  }
  return errors;
}
