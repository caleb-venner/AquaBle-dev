/**
 * Dev tab rendering
 */

import { deviceStore } from "../../../stores/deviceStore";
import type { DeviceStatus } from "../../../types/api";

/**
 * Render the dev tab - shows raw payload data for debugging
 */
export function renderDevTab(): string {
  const state = deviceStore.getState();
  
  // Convert device Map to array
  const devices: (DeviceStatus & { address: string })[] = Array.from(state.devices.values())
    .map(device => ({
      ...(device.status as DeviceStatus),
      address: device.address
    }))
    .filter(d => d.address); // Filter out devices without status

  return `
    <div style="display: flex; flex-direction: column; gap: 24px;">
      <!-- Raw Device Data -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Raw Device Data</h2>
          <div class="badge badge-info">${devices.length}</div>
        </div>
        <div style="padding: 20px;">
          ${devices.length === 0 ? `
            <div class="empty-state" style="text-align: center; color: var(--gray-500); padding: 40px 20px;">
              <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
              <h3 style="margin: 0 0 8px 0; color: var(--gray-700);">No Connected Devices</h3>
              <p style="margin: 0; color: var(--gray-500);">Connect to devices to see raw payload data for debugging.</p>
            </div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 16px;">
              ${devices.map(device => renderCollapsibleDeviceRawData(device)).join("")}
            </div>
          `}
        </div>
      </div>
    </div>
  `;
}

/**
 * Render collapsible raw data for a single device
 */
function renderCollapsibleDeviceRawData(device: any): string {
  const deviceId = `device-${device.address.replace(/:/g, '-')}`;
  const lastUpdate = device.updated_at ? new Date(device.updated_at * 1000).toLocaleString() : 'Unknown';

  return `
    <div class="device-raw-data-card" style="border: 1px solid var(--gray-200); border-radius: 8px; overflow: hidden;">
      <!-- Collapsible Header -->
      <div class="device-raw-data-header"
           onclick="window.toggleDeviceRawData('${deviceId}')"
           style="padding: 16px; background: var(--gray-50); cursor: pointer; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--gray-200);">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div class="collapse-icon" id="${deviceId}-icon" style="transition: transform 0.2s ease;">▶</div>
          <h4 style="margin: 0; color: var(--gray-900); font-size: 16px; font-weight: 600;">
            ${device.address}
          </h4>
          <div class="badge badge-secondary" style="font-size: 11px;">${device.device_type}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <div style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: ${device.connected ? 'var(--success-light)' : 'var(--gray-100)'}; border-radius: 12px; font-size: 12px; font-weight: 500; color: ${device.connected ? 'var(--success)' : 'var(--gray-600)'};">
            <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: ${device.connected ? 'var(--success)' : 'var(--gray-400)'};"></span>
            ${device.connected ? 'Connected' : 'Disconnected'}
          </div>
          <div style="font-size: 12px; color: var(--gray-500);">${lastUpdate}</div>
        </div>
      </div>

      <!-- Collapsible Content -->
      <div class="device-raw-data-content" id="${deviceId}-content" style="display: none; padding: 16px; background: var(--bg-primary);">
        <div style="margin-bottom: 16px;">
          <div style="font-size: 12px; color: var(--gray-500); margin-bottom: 4px; font-weight: 600;">Status Info</div>
          <div style="color: var(--gray-500); font-style: italic; padding: 12px; background: var(--gray-50); border-radius: 6px; border: 1px solid var(--gray-200);">Ultra-minimal DeviceStatus: only connection state. Parsed data available in device JSON files.</div>
        </div>

        <div style="margin-bottom: 16px;">
          <div style="font-size: 12px; color: var(--gray-500); margin-bottom: 8px; font-weight: 600;">Raw Status</div>
          <pre style="background: var(--gray-50); padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; margin: 0; border: 1px solid var(--gray-200);">${JSON.stringify(device, null, 2)}</pre>
        </div>
      </div>
    </div>
  `;
}
