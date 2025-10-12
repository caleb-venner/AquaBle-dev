/**
 * Light device rendering components
 */

import { getDashboardState } from "../state";
import { getWeekdayName, formatDateTime, getDeviceChannelNames } from "../../../utils";
import type { CachedStatus } from "../../../types/models";

/**
 * Render light device status
 */
export function renderLightCardStatus(device: CachedStatus & { address: string }): string {
  const parsed = device.parsed as any; // LightParsed type
  if (!parsed) {
    return `
      <div style="padding: 24px; text-align: center; color: var(--gray-500); font-size: 14px;">
        No parsed data available
      </div>
    `;
  }

  const currentTime = parsed.current_hour !== null && parsed.current_minute !== null
    ? `${String(parsed.current_hour).padStart(2, '0')}:${String(parsed.current_minute).padStart(2, '0')}`
    : 'Unknown';

  const weekdayName = parsed.weekday !== null ? getWeekdayName(parsed.weekday) : 'Unknown';

  // Create combined date/time display
  const dateTimeDisplay = currentTime !== 'Unknown' && weekdayName !== 'Unknown'
    ? formatDateTime(parsed.current_hour, parsed.current_minute, parsed.weekday)
    : 'Unknown';

  const keyframes = parsed.keyframes || [];
  const currentKeyframes = keyframes.filter((kf: any) => kf.value !== null);
  const maxBrightness = currentKeyframes.length > 0
    ? Math.max(...currentKeyframes.map((kf: any) => kf.percent || 0))
    : 0;

  // Use device type to determine channel count
  const channelNames = getDeviceChannelNames(device.address, getDashboardState);
  const channelCount = channelNames.length;

  return `
    <div style="padding: 16px; background: var(--gray-50);">
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
        <div style="background: white; padding: 12px; border-radius: 6px;">
          <div style="font-size: 11px; font-weight: 600; color: var(--gray-500); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Current Time</div>
          <div style="font-size: 16px; font-weight: 700; color: var(--gray-900);">${dateTimeDisplay}</div>
        </div>
        <div style="background: white; padding: 12px; border-radius: 6px;">
          <div style="font-size: 11px; font-weight: 600; color: var(--gray-500); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Max Brightness</div>
          <div style="font-size: 20px; font-weight: 700, color: var(--primary);">${maxBrightness}%</div>
        </div>
        <div style="background: white; padding: 12px; border-radius: 6px;">
          <div style="font-size: 11px; font-weight: 600; color: var(--gray-500); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Channels</div>
          <div style="font-size: 20px; font-weight: 700; color: var(--gray-900);">${channelCount}</div>
        </div>
      </div>
      ${renderChannelLevels(keyframes, device.channels || undefined, device.address)}
    </div>
  `;
}

/**
 * Render channel brightness levels with interactive controls
 * TODO: Controls removed in Phase 2 cleanup - will be replaced in Phase 3
 */
export function renderChannelLevels(keyframes: any[], channels?: any[], deviceAddress?: string): string {
  // Get channel names for the device to determine count
  const channelNames = deviceAddress ? getDeviceChannelNames(deviceAddress, getDashboardState) : ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'];
  const channelCount = channelNames.length;

  // Get current schedule intensity from keyframes (represents max intensity across all channels)
  const currentIntensity = keyframes.length > 0
    ? Math.max(...keyframes.map((kf: any) => kf.percent || 0))
    : 0;

  if (!deviceAddress) {
    return `
      <div style="background: white; padding: 16px; border-radius: 6px;">
        <div style="color: var(--gray-500); text-align: center; padding: 20px;">
          Device address required for channel display
        </div>
      </div>
    `;
  }

  return `
    <div style="background: white; padding: 16px; border-radius: 6px;">
      <div style="font-size: 13px; font-weight: 600; color: var(--gray-700); margin-bottom: 12px;">Channel Status</div>

      ${keyframes.length === 0 ? `
        <div style="padding: 20px; text-align: center; background: var(--gray-50); border-radius: 6px; border: 2px dashed var(--gray-300); margin-bottom: 16px;">
          <div style="font-size: 14px; color: var(--gray-600); margin-bottom: 4px;">No schedule data</div>
          <div style="font-size: 12px; color: var(--gray-500);">Device has no auto programs configured</div>
        </div>
      ` : `
        <div style="background: var(--primary-light); padding: 12px; border-radius: 6px; margin-bottom: 16px; border-left: 4px solid var(--primary);">
          <div style="font-size: 12px; font-weight: 600; color: var(--primary); margin-bottom: 4px;">Current Schedule Intensity</div>
          <div style="font-size: 16px; font-weight: 700; color: var(--primary);">${currentIntensity}%</div>
          <div style="font-size: 11px; color: var(--primary); opacity: 0.8;">Based on auto schedule (affects all channels proportionally)</div>
        </div>
      `}

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
        ${Array.from({ length: channelCount }, (_, index) => {
          const channelName = channelNames[index] || `Channel ${index + 1}`;
          return `
            <div style="background: var(--gray-50); padding: 12px; border-radius: 6px; text-align: center;">
              <div style="font-size: 12px; font-weight: 600; color: var(--gray-700); margin-bottom: 4px;">${channelName}</div>
              <div style="font-size: 14px; color: var(--gray-500);">—</div>
            </div>
          `;
        }).join('')}
      </div>

      <div style="margin-top: 12px; padding: 8px 12px; background: var(--gray-100); border-radius: 4px; font-size: 11px; color: var(--gray-600);">
        💡 <strong>Note:</strong> Individual channel values are not reported by the device. Channel controls will be available in a future update.
      </div>
    </div>
  `;
}
