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
            onclick="window.handleRefreshDevice('${device.address}')"
            title="Refresh Status"
            style="padding: 6px 10px; font-size: 16px; background: transparent; border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer; color: var(--text-secondary); transition: all 0.2s;"
            onmouseover="this.style.background='var(--gray-100)'; this.style.borderColor='var(--gray-400)'; this.style.color='var(--text-primary)';"
            onmouseout="this.style.background='transparent'; this.style.borderColor='var(--border-color)'; this.style.color='var(--text-secondary)';"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="display: block;">
              <path d="M17.65,6.35C16.2,4.9,14.21,4,12,4A8,8,0,0,0,4,12A8,8,0,0,0,12,20C15.73,20,18.84,17.45,19.73,14H17.65C16.83,16.33,14.61,18,12,18A6,6,0,0,1,6,12A6,6,0,0,1,12,6C13.66,6,15.14,6.69,16.22,7.78L13,11H20V4L17.65,6.35Z" />
            </svg>
          </button>
          <button
            class="btn-icon"
            onclick="window.handleDeviceSettings('${device.address}', '${device.device_type}')"
            title="Device Settings"
            style="padding: 6px 10px; font-size: 16px; background: transparent; border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer; color: var(--text-secondary); transition: all 0.2s;"
            onmouseover="this.style.background='var(--gray-100)'; this.style.borderColor='var(--gray-400)'; this.style.color='var(--text-primary)';"
            onmouseout="this.style.background='transparent'; this.style.borderColor='var(--border-color)'; this.style.color='var(--text-secondary)';"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="display: block;"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" /></svg>
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
