/**
 * Doser device rendering components
 */

import { deviceStore } from "../../../stores/deviceStore";
import { getDoserHeadName, getHeadConfigData } from "../utils/device-utils";
import type { DeviceStatus } from "../../../types/api";

/**
 * Render doser device status
 */
export function renderDoserCardStatus(device: DeviceStatus & { address: string }): string {
  const zustandState = deviceStore.getState();
  const config = zustandState.configurations.dosers.get(device.address);
  
  // If we have parsed status data, show the pump heads
  if (config?.last_status?.parsed?.heads) {
    return renderPumpHeads(config.last_status.parsed.heads, config, device.address);
  }
  
  // Fallback: show simple connection state when parsed data isn't available yet
  return `
    <div style="padding: 24px; text-align: center; color: var(--gray-500); font-size: 14px;">
      <div style="font-size: 16px; color: ${device.connected ? 'var(--success)' : 'var(--gray-400)'}; margin-bottom: 8px;">
        ${device.connected ? '✓ Connected' : '○ Disconnected'}
      </div>
      <div style="font-size: 12px;">
        Last update: ${new Date(device.updated_at * 1000).toLocaleTimeString()}
      </div>
    </div>
  `;
}

/**
 * Render pump heads grid
 */
function renderPumpHeads(heads: any[], savedConfig?: any, deviceAddress?: string): string {
  // Always show 4 heads (standard for doser devices)
  // Combine device status data with configuration data
  const allHeads = [];

  for (let i = 0; i < 4; i++) {
    const deviceHead = heads[i];
    const headIndex = i + 1; // 1-based indexing for heads

    // Get configuration data for this head
    const configData = deviceAddress ? getHeadConfigData(headIndex, deviceAddress) : { setDose: 'N/A', schedule: 'N/A' };

    // Get custom head name from metadata (pass 1-based index)
    const customName = deviceAddress ? getDoserHeadName(deviceAddress, headIndex) : null;

    // Get dosed today from device head
    const dosedToday = deviceHead?.dosed_tenths_ml ? `${(deviceHead.dosed_tenths_ml / 10).toFixed(1)}mL` : 'N/A';

    allHeads.push({
      index: headIndex,
      deviceHead,
      configData,
      customName,
      dosedToday
    });
  }

  return `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
      ${allHeads.map((head: any) => renderPumpHead(head)).join('')}
    </div>
  `;
}

/**
 * Render a single pump head
 */
function renderPumpHead(head: any): string {
  const { index, deviceHead, configData, customName, dosedToday } = head;

  // Determine head status and mode
  let statusText = 'Disabled';
  let statusColor = 'var(--gray-400)';
  let modeText = 'N/A';
  let isDisabled = true;

  if (deviceHead) {
    // Head status: {0,1,2,3,4} = {Daily, 24 Hourly, Custom, Timer, Disabled}
    const mode = deviceHead.mode;
    switch (mode) {
      case 0:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = 'Daily';
        isDisabled = false;
        break;
      case 1:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = '24H';
        isDisabled = false;
        break;
      case 2:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = 'Custom';
        isDisabled = false;
        break;
      case 3:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = 'Timer';
        isDisabled = false;
        break;
      case 4:
      default:
        statusText = 'Disabled';
        statusColor = 'var(--gray-400)';
        modeText = 'Disabled';
        isDisabled = true;
        break;
    }
  }

  const headName = customName || `Head ${index}`;

  // If disabled, show simple view
  if (isDisabled) {
    return `
      <div style="padding: 8px 12px; background: var(--bg-primary); border-radius: 4px; border-left: 3px solid ${statusColor};">
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center;">
          <div style="font-size: 13px; font-weight: 600; color: var(--text-primary);">${headName}</div>
          <div style="font-size: 11px; color: ${statusColor}; font-weight: 600;">${statusText}</div>
        </div>
      </div>
    `;
  }

  return `
    <div style="padding: 8px 12px; background: var(--bg-primary); border-radius: 4px; border-left: 3px solid ${statusColor};">
      <!-- First Row: Head name, mode, status -->
      <div style="display: grid; grid-template-columns: 1fr auto auto; gap: 8px; align-items: center; margin-bottom: 8px;">
        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary);">${headName}</div>
        <div style="font-size: 11px; color: var(--text-secondary);">${modeText}</div>
        <div style="font-size: 11px; color: ${statusColor}; font-weight: 600;">${statusText}</div>
      </div>

      <!-- Second Row: Set Dose, Schedule, Dosed Today -->
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 11px;">
        <div style="text-align: center;">
          <div style="color: var(--text-secondary); margin-bottom: 2px;">Set Dose</div>
          <div style="font-weight: 600; color: var(--text-primary);">${configData.setDose}</div>
        </div>
        <div style="text-align: center;">
          <div style="color: var(--text-secondary); margin-bottom: 2px;">Schedule</div>
          <div style="font-weight: 600; color: var(--text-primary);">${configData.schedule}</div>
        </div>
        <div style="text-align: center;">
          <div style="color: var(--text-secondary); margin-bottom: 2px;">Dosed</div>
          <div style="font-weight: 600; color: var(--text-primary);">${dosedToday}</div>
        </div>
      </div>
    </div>
  `;
}
