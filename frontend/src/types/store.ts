/**
 * Frontend Store Types
 * UI state management types for Zustand store
 */

import type { DeviceStatus, CommandRequest } from './api';

// ========================================
// DEVICE STATE MANAGEMENT
// ========================================

/** Union type for device configurations - import from API */
export type DeviceConfiguration = import('../api/configurations').DoserDevice | import('../api/configurations').LightDevice;

/** Individual device state for UI */
export interface DeviceState {
  address: string;
  status: DeviceStatus | null; // Runtime state (can be null if device hasn't been seen yet)
  configuration: DeviceConfiguration | null; // Saved configuration (names, settings)
  lastUpdated: number;
  isLoading: boolean;
  error: string | null;
}

/** Helper type for device entries */
export interface DeviceEntry {
  address: string;
  status: DeviceStatus;
}

// ========================================
// COMMAND QUEUE
// ========================================

/** Command queue entry */
export interface QueuedCommand {
  id: string;
  address: string;
  request: CommandRequest;
  queuedAt: number;
  retryCount: number;
}

// ========================================
// APPLICATION UI STATE
// ========================================

/** Application-wide UI state */
export interface UIState {
  currentView: "dashboard" | "overview" | "dev";
  globalError: string | null;
  notifications: Notification[];
}

/** User notification */
export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
  timestamp: number;
  autoHide?: boolean;
}

// ========================================
// FORM PAYLOADS
// ========================================

/** Form data for manual brightness control */
export interface ManualBrightnessPayload {
  index: number;
  value: number;
}
