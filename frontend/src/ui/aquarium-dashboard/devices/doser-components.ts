/**
 * Doser device rendering components
 */

import { deviceStore } from "../../../stores/deviceStore";
import { formatDateTime, getWeekdayName } from "../../../utils";
import { getDoserHeadName, getHeadConfigData } from "../utils/device-utils";
import type { CachedStatus } from "../../../types/models";

/**
 * Render doser device status
 */
export function renderDoserCardStatus(device: CachedStatus & { address: string }): string {
  const parsed = device.parsed as any; // DoserParsed type
  if (!parsed) {
    return `
      <div style="padding: 24px; text-align: center; color: var(--gray-500); font-size: 14px;">
        No parsed data available
      </div>
    `;
  }

  const currentTime = parsed.hour !== null && parsed.minute !== null
    ? `${String(parsed.hour).padStart(2, '0')}:${String(parsed.minute).padStart(2, '0')}`
    : 'Unknown';

  const weekdayName = parsed.weekday !== null ? getWeekdayName(parsed.weekday) : 'Unknown';

  // Create combined date/time display
  const dateTimeDisplay = currentTime !== 'Unknown' && weekdayName !== 'Unknown'
    ? formatDateTime(parsed.hour, parsed.minute, parsed.weekday)
    : 'Unknown';

  const heads = parsed.heads || [];

  // Count active heads: status != 4 (Disabled)
  // Head status: {0,1,2,3,4} = {Daily, 24 Hourly, Custom, Timer, Disabled}
  const activeHeads = heads.filter((head: any) => head.mode !== 4).length;

  // Find the saved configuration for this device
  const zustandState = deviceStore.getState();
  const savedConfig = zustandState.configurations.dosers.get(device.address);

  return `
    <div style="padding: 16px; background: var(--bg-secondary);">
      ${renderPumpHeads(heads, savedConfig, device.address)}
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

    // Get custom head name from metadata
    const customName = deviceAddress ? getDoserHeadName(deviceAddress, i) : null;

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
    <div style="background: var(--card-bg); padding: 16px; border-radius: 6px; border: 1px solid var(--border-color);">
      <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px;">Pump Heads</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        ${allHeads.map((head: any) => renderPumpHead(head)).join('')}
      </div>
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

  if (deviceHead) {
    // Head status: {0,1,2,3,4} = {Daily, 24 Hourly, Custom, Timer, Disabled}
    const mode = deviceHead.mode;
    switch (mode) {
      case 0:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = 'Daily';
        break;
      case 1:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = '24H';
        break;
      case 2:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = 'Custom';
        break;
      case 3:
        statusText = 'Active';
        statusColor = 'var(--success)';
        modeText = 'Timer';
        break;
      case 4:
      default:
        statusText = 'Disabled';
        statusColor = 'var(--gray-400)';
        modeText = 'Disabled';
        break;
    }
  }

  const headName = customName || `Head ${index}`;

  return `
    <div style="background: var(--gray-50); padding: 12px; border-radius: 6px; border-left: 3px solid ${statusColor};">
      <!-- First Row: Head name, mode, status -->
      <div style="display: grid; grid-template-columns: 1fr auto auto; gap: 8px; align-items: center; margin-bottom: 8px;">
        <div style="font-size: 13px; font-weight: 600; color: var(--gray-900);">${headName}</div>
        <div style="font-size: 11px; color: var(--gray-500);">${modeText}</div>
        <div style="font-size: 11px; color: ${statusColor}; font-weight: 600;">${statusText}</div>
      </div>

      <!-- Second Row: Set Dose, Schedule, Dosed Today -->
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 11px;">
        <div style="text-align: center;">
          <div style="color: var(--gray-500); margin-bottom: 2px;">Set Dose</div>
          <div style="font-weight: 600; color: var(--gray-900);">${configData.setDose}</div>
        </div>
        <div style="text-align: center;">
          <div style="color: var(--gray-500); margin-bottom: 2px;">Schedule</div>
          <div style="font-weight: 600; color: var(--gray-900);">${configData.schedule}</div>
        </div>
        <div style="text-align: center;">
          <div style="color: var(--gray-500); margin-bottom: 2px;">Dosed</div>
          <div style="font-weight: 600; color: var(--gray-900);">${dosedToday}</div>
        </div>
      </div>
    </div>
  `;
}
