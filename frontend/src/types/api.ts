// Backend API Model Interfaces
// These types match the Python backend models and API responses

// ========================================
// COMMAND MODELS
// ========================================

/** Matches Python CommandStatus Literal */
export type CommandStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "timed_out"
  | "cancelled";

/** Matches Python CommandRecord dataclass */
export interface CommandRecord {
  id: string;
  address: string;
  action: string;
  args: Record<string, unknown> | null;
  status: CommandStatus;
  attempts: number;
  result: Record<string, unknown> | null;
  error: string | null;
  error_code: string | null;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  timeout: number;
}

/** Matches Python CommandRequest model */
export interface CommandRequest {
  id?: string;
  action: string;
  args?: Record<string, unknown>;
  timeout?: number;
}

// ========================================
// DEVICE STATUS MODELS
// ========================================

/** Light device channel definition */
export interface LightChannel {
  index: number;         // Channel index (0, 1, 2, 3)
  key: string;           // Channel index as string ("0", "1", "2", "3")
  label: string;         // Human-readable name ("Red", "Green", "Blue", "White")
}

/** Light device parsed status (matches serialize_light_status) */
export interface LightParsed {
  message_id: number;
  response_mode: number;
  weekday: number | null;
  current_hour: number | null;
  current_minute: number | null;
  keyframes: LightKeyframe[];
  time_markers: number[];
  tail: string; // hex string
}

/** Light keyframe with computed percentage */
export interface LightKeyframe {
  index: number;
  timestamp: number;
  value: number | null;
  percent: number; // computed percentage (0-100)
}

/** Doser head information */
export interface DoserHead {
  mode: number;
  hour: number;
  minute: number;
  dosed_tenths_ml: number;
  extra: string; // hex string
  mode_label: string; // human-friendly mode name
}

/** Doser device parsed status (matches serialize_doser_status) */
export interface DoserParsed {
  weekday: number | null;
  hour: number | null;
  minute: number | null;
  heads: DoserHead[];
  tail_raw: string; // hex string
  lifetime_totals_tenths_ml: number[]; // lifetime totals in tenths of mL for each head
}

/**
 * Device runtime status (ultra-minimal, connection state only)
 * Matches cached_status_to_dict output structure from backend.
 * 
 * This contains ONLY runtime connection state for efficient polling.
 * Device names, configurations, parsed status, and raw payloads are
 * available via /api/devices/{address}/configurations endpoint.
 */
export interface DeviceStatus {
  address: string;
  device_type: "light" | "doser";
  connected: boolean;
  updated_at: number;
}

// Deprecated alias for backward compatibility
/** @deprecated Use DeviceStatus instead - CachedStatus is an outdated name */
export type CachedStatus = DeviceStatus;

// ========================================
// API RESPONSE MODELS
// ========================================

/** Main status endpoint response */
export interface StatusResponse {
  [address: string]: DeviceStatus;
}

/** Device scan result */
export interface ScanDevice {
  address: string;
  name: string;
  product: string;
  device_type: "light" | "doser";
}

// ========================================
// COMMAND ARGUMENT INTERFACES
// ========================================

/** Arguments for set_brightness command */
export interface SetBrightnessArgs {
  brightness: number; // 0-100
  color: number; // 0-5, channel index
}

/** Arguments for add_auto_setting command */
export interface AddAutoSettingArgs {
  sunrise: string; // HH:MM format
  sunset: string; // HH:MM format
  brightness?: number; // 0-100, for single channel (legacy)
  channels?: Record<string, number>; // Per-channel brightness values
  ramp_up_minutes?: number; // default 0
  weekdays?: string[]; // e.g., ["monday", "tuesday"]
}

/** Arguments for set_schedule command (doser) */
export interface SetScheduleArgs {
  head_index: number; // 1-4
  volume_tenths_ml: number; // 0-255
  hour: number; // 0-23
  minute: number; // 0-59
  weekdays?: string[]; // e.g., ["monday", "tuesday"]
  confirm?: boolean; // default true
  wait_seconds?: number; // default 2.0
}

// ========================================
// LEGACY COMPATIBILITY
// ========================================

/** @deprecated Legacy interface - all functionality now in DeviceStatus (defined above) */
