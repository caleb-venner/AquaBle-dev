// UI-Specific Model Interfaces
// These types are used for frontend state management and UI logic

import type { CachedStatus, CommandRequest } from './backend-models';

// ========================================
// DEVICE STATE MANAGEMENT
// ========================================

/** Union type for device configurations - import from API */
export type DeviceConfiguration = import('../api/configurations').DoserDevice | import('../api/configurations').LightDevice;

/** Individual device state for UI */
export interface DeviceState {
  address: string;
  status: CachedStatus | null; // Can be null if device hasn't been seen yet
  configuration: DeviceConfiguration | null; // Saved configuration
  lastUpdated: number;
  isLoading: boolean;
  error: string | null;
}

/** Helper type for device entries */
export interface DeviceEntry {
  address: string;
  status: CachedStatus;
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
