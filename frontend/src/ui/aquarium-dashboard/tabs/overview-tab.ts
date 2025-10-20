/**
 * Overview tab rendering
 */

import { deviceStore } from "../../../stores/deviceStore";
import type { CachedStatus } from "../../../types/models";
import { renderDeviceSection } from "../devices/device-card";

/**
 * Render the overview tab - shows device connection status
 */
export function renderOverviewTab(): string {
  const state = deviceStore.getState();

  // Convert device Map to array of connected devices
  const devices: (CachedStatus & { address: string })[] = Array.from(state.devices.values())
    .filter(device => device.status?.connected)
    .map(device => ({
      ...(device.status as CachedStatus),
      address: device.address
    }));

  // Show empty state if no devices
  if (devices.length === 0) {
    return `
      <div class="empty-state">
        <h2>No Devices Connected</h2>
        <p>This dashboard shows the status of connected aquarium devices. Devices must be connected externally to the backend service.</p>
      </div>
    `;
  }

  return `
    ${renderDeviceSection("Connected Devices", devices)}
  `;
}
