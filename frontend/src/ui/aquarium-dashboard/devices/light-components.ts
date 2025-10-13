/**
 * Light device rendering components
 */

import { getDashboardState } from "../state";
import { getWeekdayName, formatDateTime, getDeviceChannelNames } from "../../../utils";
import { getCurrentScheduleInfo, AutoProgram, getAllSchedulesInOrder, SequentialSchedule } from "../../../utils/schedule-utils";
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

  // Get all schedules in sequential order
  const allSchedules = getAllSchedulesInOrder(autoPrograms);

  return `
    <div style="padding: 16px; background: var(--bg-secondary);">
      ${allSchedules.length > 0 ? `
        <div style="background: var(--card-bg); padding: 12px; border-radius: 6px; margin-bottom: 16px; border: 1px solid var(--border-color);">
          <div style="font-size: 11px; font-weight: 600; color: var(--gray-500); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Light Schedules</div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${allSchedules.map(schedule => renderScheduleItem(schedule)).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * Render a single schedule item with color coding
 */
function renderScheduleItem(schedule: SequentialSchedule): string {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'current': return 'var(--success)'; // Green
      case 'next': return 'var(--primary)'; // Blue
      case 'upcoming': return 'var(--gray-400)'; // Grey
      case 'disabled': return 'var(--error)'; // Red
      default: return 'var(--gray-400)';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'current': return 'Active';
      case 'next': return 'Next';
      case 'upcoming': return 'Upcoming';
      case 'disabled': return 'Disabled';
      default: return 'Unknown';
    }
  };

  const accentColor = getStatusColor(schedule.status);
  const statusText = getStatusText(schedule.status);

  // Format channel levels (WRGB values)
  const channelLevels = Object.entries(schedule.program.levels)
    .map(([channel, value]) => `${channel.charAt(0).toUpperCase()}:${value}%`)
    .join(' ');

  // Format time range with day prefix if nextTime exists
  let timeRange: string;
  if (schedule.nextTime) {
    // Extract day from nextTime (e.g., "today at 13:00" -> "today")
    const dayPrefix = schedule.nextTime.split(' at ')[0];
    timeRange = `${dayPrefix} ${schedule.program.sunrise} - ${schedule.program.sunset}`;
  } else {
    timeRange = `${schedule.program.sunrise} - ${schedule.program.sunset}`;
  }

  return `
    <div style="padding: 8px 12px; background: var(--bg-primary); border-radius: 4px; border-left: 3px solid ${accentColor};">
      <div style="flex: 1; min-width: 0;">
        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">${schedule.program.label}</div>
        <div style="font-size: 11px; color: var(--text-secondary);">
          ${statusText} • ${timeRange} • ${schedule.program.rampMinutes}min ramp
        </div>
        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
          ${channelLevels}
        </div>
      </div>
    </div>
  `;
}
