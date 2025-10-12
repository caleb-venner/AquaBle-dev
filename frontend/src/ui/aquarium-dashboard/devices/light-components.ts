/**
 * Light device rendering components
 */

import { getDashboardState } from "../state";
import { getWeekdayName, formatDateTime, getDeviceChannelNames } from "../../../utils";
import { getCurrentScheduleInfo, AutoProgram } from "../../../utils/schedule-utils";
import { getDeviceStore } from "../../../stores/deviceStore";
import type { CachedStatus } from "../../../types/models";

/**
 * Extract auto programs from device configuration
 */
function getDeviceAutoPrograms(deviceAddress: string): AutoProgram[] {
  const store = getDeviceStore();
  const state = store.getState();
  const deviceConfig = state.configurations.lights.get(deviceAddress);

  if (!deviceConfig?.configurations) {
    return [];
  }

  const activeConfig = deviceConfig.configurations.find(
    (config: any) => config.id === deviceConfig.activeConfigurationId
  );

  if (!activeConfig?.revisions || activeConfig.revisions.length === 0) {
    return [];
  }

  const latestRevision = activeConfig.revisions[activeConfig.revisions.length - 1];
  const profile = latestRevision.profile;

  if (profile.mode !== 'auto' || !profile.programs) {
    return [];
  }

  return profile.programs.map((program: any) => ({
    id: program.id,
    label: program.label,
    enabled: program.enabled,
    days: program.days,
    sunrise: program.sunrise,
    sunset: program.sunset,
    rampMinutes: program.rampMinutes,
    levels: program.levels
  }));
}

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

  // Get schedule information for auto mode devices
  const autoPrograms = getDeviceAutoPrograms(device.address);
  const scheduleInfo = getCurrentScheduleInfo(autoPrograms);

  return `
    <div style="padding: 16px; background: var(--bg-secondary);">
      ${scheduleInfo.type !== 'none' ? `
        <div style="background: var(--card-bg); padding: 12px; border-radius: 6px; margin-bottom: 16px; border: 1px solid var(--border-color); border-left: 4px solid ${scheduleInfo.type === 'current' ? 'var(--success)' : 'var(--primary)'};">
          <div style="font-size: 11px; font-weight: 600; color: var(--gray-500); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Schedule Status</div>
          <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">${scheduleInfo.status}</div>
          ${scheduleInfo.nextTime ? `<div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">${scheduleInfo.nextTime}</div>` : ''}
          ${scheduleInfo.program ? `
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px;">
              <div><span style="color: var(--gray-500);">Sunrise:</span> ${scheduleInfo.program.sunrise}</div>
              <div><span style="color: var(--gray-500);">Sunset:</span> ${scheduleInfo.program.sunset}</div>
              <div><span style="color: var(--gray-500);">Ramp:</span> ${scheduleInfo.program.rampMinutes}min</div>
              <div><span style="color: var(--gray-500);">Channels:</span> ${Object.entries(scheduleInfo.program.levels).map(([key, value]) => `${key.charAt(0).toUpperCase()}:${value}%`).join(' ')}</div>
            </div>
          ` : ''}
        </div>
      ` : ''}
    </div>
  `;
}
