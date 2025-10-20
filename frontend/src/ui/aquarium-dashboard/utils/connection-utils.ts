/**
 * Connection status utilities
 */

import type { CachedStatus } from "../../../types/models";
import type { ConnectionStability } from "../types";

export type ConnectionHealth = 'stable' | 'unstable' | 'disconnected' | 'reconnecting';

/**
 * Determine overall connection health based on device status and stability tracking
 */
export function getConnectionHealth(deviceStatus: CachedStatus | null): ConnectionHealth {
  if (!deviceStatus) {
    return 'disconnected';
  }

  // If device is not connected according to status
  if (!deviceStatus.connected) {
    return 'disconnected';
  }

  return 'stable';
}

/**
 * Get connection status display information
 */
export function getConnectionStatusDisplay(health: ConnectionHealth): {
  color: string;
  title: string;
} {
  switch (health) {
    case 'stable':
      return {
        color: '#10b981', // green-500 - matches typical "on" button color
        title: 'Stable'
      };
    case 'unstable':
      return {
        color: '#f59e0b', // amber-500 - warning orange
        title: 'Unstable'
      };
    case 'disconnected':
      return {
        color: '#ef4444', // red-500 - matches typical "off" button color
        title: 'Disconnected'
      };
    case 'reconnecting':
      return {
        color: '#3b82f6', // blue-500 - reconnecting state
        title: 'Reconnecting'
      };
  }
}

/**
 * Render connection status badge
 */
export function renderConnectionStatus(deviceStatus: CachedStatus | null): string {
  const health = getConnectionHealth(deviceStatus);
  const display = getConnectionStatusDisplay(health);

  return `
    <div class="connection-indicator" title="${display.title}" style="
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background-color: ${display.color};
      border: 2px solid white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      cursor: help;
    "></div>
  `;
}

/**
 * Render larger connection status for modals (inline with close button)
 */
export function renderModalConnectionStatus(deviceStatus: CachedStatus | null): string {
  const health = getConnectionHealth(deviceStatus);
  const display = getConnectionStatusDisplay(health);

  return `
    <div class="connection-indicator-modal" title="${display.title}" style="
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background-color: ${display.color};
      border: 3px solid white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      cursor: help;
    "></div>
  `;
}

/**
 * Get user-friendly message for connection issues
 */
export function getConnectionMessage(health: ConnectionHealth): string | null {
  switch (health) {
    case 'unstable':
      return 'This device is experiencing connection issues. Commands may be slow or fail.';
    case 'disconnected':
      return 'This device is not connected. Try refreshing or reconnecting the device.';
    default:
      return null;
  }
}
