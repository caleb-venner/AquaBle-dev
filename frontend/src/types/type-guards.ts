// Type Guard Functions and Type Predicates
// These functions help with runtime type checking and narrowing

import type { CachedStatus, LightParsed, DoserParsed, CommandRecord, CommandStatus } from './backend-models';

// ========================================
// DEVICE TYPE GUARDS
// ========================================

export function isLightDevice(device: CachedStatus): device is CachedStatus & { device_type: "light" } {
  return device.device_type === "light";
}

export function isDoserDevice(device: CachedStatus): device is CachedStatus & { device_type: "doser" } {
  return device.device_type === "doser";
}

export function isLightParsed(parsed: unknown): parsed is LightParsed {
  return typeof parsed === "object" && parsed !== null && "keyframes" in parsed;
}

export function isDoserParsed(parsed: unknown): parsed is DoserParsed {
  return typeof parsed === "object" && parsed !== null && "heads" in parsed;
}

// ========================================
// COMMAND STATUS TYPE GUARDS
// ========================================

/** Check if command is complete */
export function isCommandComplete(command: CommandRecord): boolean {
  return ["success", "failed", "timed_out", "cancelled"].includes(command.status);
}

/** Check if command was successful */
export function isCommandSuccessful(command: CommandRecord): boolean {
  return command.status === "success";
}

/** Get human-readable command status */
export function getCommandStatusLabel(status: CommandStatus): string {
  switch (status) {
    case "pending": return "Pending";
    case "running": return "Running";
    case "success": return "Success";
    case "failed": return "Failed";
    case "timed_out": return "Timed Out";
    case "cancelled": return "Cancelled";
    default: return "Unknown";
  }
}
