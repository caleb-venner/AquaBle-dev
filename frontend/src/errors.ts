/** Error types and constants for consistent error handling in the frontend. */

export enum ErrorCode {
  // Device-related errors
  DEVICE_NOT_FOUND = "device_not_found",
  DEVICE_DISCONNECTED = "device_disconnected",
  DEVICE_BUSY = "device_busy",
  DEVICE_TIMEOUT = "device_timeout",

  // Command-related errors
  COMMAND_INVALID = "command_invalid",
  COMMAND_TIMEOUT = "command_timeout",
  COMMAND_FAILED = "command_failed",
  COMMAND_CANCELLED = "command_cancelled",

  // Validation errors
  VALIDATION_ERROR = "validation_error",
  INVALID_ARGUMENTS = "invalid_arguments",

  // BLE-specific errors
  BLE_CONNECTION_ERROR = "ble_connection_error",
  BLE_CHARACTERISTIC_MISSING = "ble_characteristic_missing",

  // Configuration errors
  CONFIG_SAVE_ERROR = "config_save_error",

  // Generic errors
  INTERNAL_ERROR = "internal_error",
  UNKNOWN_ERROR = "unknown_error",
}

export interface AquariumError {
  code: ErrorCode;
  message: string;
  details?: Record<string, any>;
}

/** Get user-friendly error message for an error code */
export function getErrorMessage(error: AquariumError | null): string {
  if (!error) return "Unknown error occurred";

  switch (error.code) {
    case ErrorCode.DEVICE_NOT_FOUND:
      return "Device not found. Please check that the device is powered on and in range.";
    case ErrorCode.DEVICE_DISCONNECTED:
      return "Device is disconnected. Please reconnect and try again.";
    case ErrorCode.DEVICE_BUSY:
      return "Device is busy processing another command. Please wait and try again.";
    case ErrorCode.DEVICE_TIMEOUT:
      return "Device communication timed out. Please check the connection and try again.";
    case ErrorCode.COMMAND_TIMEOUT:
      return "Command timed out. The operation may have completed - please check device status.";
    case ErrorCode.VALIDATION_ERROR:
      return `Invalid input: ${error.message}`;
    case ErrorCode.INVALID_ARGUMENTS:
      return `Invalid arguments: ${error.message}`;
    case ErrorCode.BLE_CONNECTION_ERROR:
      return "Bluetooth connection failed. Please check device connectivity.";
    case ErrorCode.BLE_CHARACTERISTIC_MISSING:
      return "Device communication error. The device may not be compatible.";
    case ErrorCode.CONFIG_SAVE_ERROR:
      return "Failed to save configuration. Settings may not persist.";
    case ErrorCode.INTERNAL_ERROR:
      return "An internal error occurred. Please try again or contact support.";
    default:
      return error.message || "An unexpected error occurred.";
  }
}
