/**
 * Overview tab rendering
 */

import { deviceStore } from "../../../stores/deviceStore";
import type { DeviceStatus } from "../../../types/api";
import { renderDeviceSection } from "../devices/device-card";

/**
 * Render the overview tab - shows device connection status
 */
export function renderOverviewTab(): string {
  const state = deviceStore.getState();

  // Convert device Map to array of connected devices
  const devices: (DeviceStatus & { address: string })[] = Array.from(state.devices.values())
    .filter(device => device.status?.connected)
    .map(device => ({
      ...(device.status as DeviceStatus),
      address: device.address
    }));

  // Always render the device section, even if empty
  // This ensures the scan button is always accessible
  return `
    ${renderDeviceSection("Devices", devices)}
  `;
}
