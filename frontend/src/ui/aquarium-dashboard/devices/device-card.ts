/**
 * Device card rendering functions
 */

import { deviceStore } from "../../../stores/deviceStore";
import { getTimeAgo } from "../../../utils";
/* import { renderConnectionStatus } from "../utils/connection-utils"; */
import { renderLightCardStatus/* , renderChannelLevels */ } from "./light-components";
import { renderDoserCardStatus } from "./doser-components";
import type { DeviceStatus } from "../../../types/api";

/**
 * Render a device section with device tiles
 */
export function renderDeviceSection(
  title: string,
  devices: Array<DeviceStatus & { address: string }>
): string {
  return `
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">${title}</h2>
        <div class="badge badge-info">${devices.length}</div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-top: 16px;">
        ${devices.map(device => renderDeviceTile(device)).join("")}
      </div>
    </div>
  `;
}

/**
 * Render an individual device tile with full device info
 * TODO: Simplified per dashboard cleanup - only showing header
 */
function renderDeviceTile(device: DeviceStatus & { address: string }): string {
  const statusColor = device.connected ? "var(--success)" : "var(--gray-400)";
  const statusText = device.connected ? "Connected" : "Disconnected";
  
  // Get device name from configuration (all devices have 'name' field)
  const zustandState = deviceStore.getState();
  const config = device.device_type === "doser" 
    ? zustandState.configurations.dosers.get(device.address)
    : zustandState.configurations.lights.get(device.address);
  
  const deviceName = config?.name || device.address;
  const timeAgo = getTimeAgo(device.updated_at);

  return `
    <div class="card device-card ${device.device_type} ${device.connected ? 'connected' : 'disconnected'}" style="padding: 0; border-left: 4px solid ${statusColor};">
      ${renderDeviceCardHeader(device, deviceName, statusText, timeAgo)}
      ${renderDeviceCardBody(device)}
      ${renderDeviceCardFooter(device)}
    </div>
  `;
}

/**
 * Render device card header
 */
function renderDeviceCardHeader(
  device: DeviceStatus & { address: string },
  deviceName: string,
  statusText: string,
  timeAgo: string
): string {
  const statusColor = device.connected ? "var(--success)" : "var(--gray-400)";

  return `
    <div class="device-header" style="padding: 16px; border-bottom: 1px solid var(--border-color);">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div class="status-indicator" style="width: 12px; height: 12px; border-radius: 50%; background: ${statusColor};"></div>
          <h3 style="font-size: 18px; font-weight: 600; margin: 0; color: var(--text-primary);">
            ${deviceName}
          </h3>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <button
            class="btn-icon"
            onclick="window.handleDeviceSettings('${device.address}', '${device.device_type}')"
            title="Device Settings"
            style="padding: 6px 10px; font-size: 16px; background: transparent; border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer; color: var(--text-secondary); transition: all 0.2s;"
            onmouseover="this.style.background='var(--gray-100)'; this.style.borderColor='var(--gray-400)'; this.style.color='var(--text-primary)';"
            onmouseout="this.style.background='transparent'; this.style.borderColor='var(--border-color)'; this.style.color='var(--text-secondary)';"
          >
            ⚙
          </button>
          <div style="font-size: 11px; color: var(--text-secondary);">${timeAgo}</div>
        </div>
      </div>
    </div>
  `;
}

/**
 * Render device card body (device info/status section)
 */
function renderDeviceCardBody(device: DeviceStatus & { address: string }): string {
  return `
    <div class="device-body" style="padding: 16px;">
      ${renderDeviceSpecificContent(device)}
    </div>
  `;
}

/**
 * Render device-specific content based on device type
 */
function renderDeviceSpecificContent(device: DeviceStatus & { address: string }): string {
  if (device.device_type === "light") {
    return renderLightCardStatus(device);
  } else if (device.device_type === "doser") {
    return renderDoserCardStatus(device);
  } else {
    return `
      <div class="device-status-placeholder">
        <div style="text-align: center; color: var(--gray-500); padding: 20px;">
          <div style="font-size: 24px; margin-bottom: 8px;">📊</div>
          <p>Device status and information will be displayed here</p>
        </div>
      </div>
    `;
  }
}

/**
 * Render device card footer (Settings and Connect buttons)
 */
function renderDeviceCardFooter(device: DeviceStatus & { address: string }): string {
  const connectButtonText = device.connected ? 'Disconnect' : 'Connect';
  const connectButtonClass = device.connected ? 'btn-danger' : 'btn-primary';

  return `
    <div class="device-footer" style="padding: 16px; border-top: 1px solid var(--border-color); background: var(--bg-secondary);">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <button class="btn btn-outline" onclick="window.openDeviceSettings('${device.address}', '${device.device_type}')">
          Settings
        </button>
        <button class="btn connect-button ${connectButtonClass}" onclick="window.toggleDeviceConnection('${device.address}')">
          ${connectButtonText}
        </button>
      </div>
    </div>
  `;
}
