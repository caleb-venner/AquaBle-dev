/**
 * Overview tab rendering
 */

import { getDashboardState } from "../state";
import { renderDeviceSection } from "../devices/device-card";

/**
 * Render the overview tab - shows device connection status
 */
export function renderOverviewTab(): string {
  const state = getDashboardState();

  // Convert StatusResponse object to array
  const devices = Object.entries(state.deviceStatus || {}).map(([address, status]) => ({
    ...status,
    address
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
