/**
 * Light device rendering components
 */

import { deviceStore } from "../../../stores/deviceStore";
import { getWeekdayName, formatDateTime } from "../../../utils";
import type { AutoProgram } from "../../../utils/schedule-utils";
import type { DeviceStatus } from "../../../types/api";

/**
 * Extract auto programs from device configuration
 */
function getDeviceAutoPrograms(deviceAddress: string): (AutoProgram & { channels?: any[] })[] {
  const state = deviceStore.getState();
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

  // The backend now provides the 'status' field directly.
  // We just need to merge the 'channels' for rendering.
  return profile.programs.map((program: any) => ({
    ...program,
    channels: deviceConfig.channels,
  }));
}

/**
 * Render light device status
 */
export function renderLightCardStatus(device: DeviceStatus & { address: string }): string {
  const state = deviceStore.getState();
  const deviceConfig = state.configurations.lights.get(device.address);

  // Check if device is in auto mode and has programs
  if (deviceConfig?.configurations && deviceConfig.activeConfigurationId) {
    const activeConfig = deviceConfig.configurations.find(
      (config: any) => config.id === deviceConfig.activeConfigurationId
    );

    if (activeConfig?.revisions && activeConfig.revisions.length > 0) {
      const latestRevision = activeConfig.revisions[activeConfig.revisions.length - 1];
      const profile = latestRevision.profile;

      // If in auto mode and has programs, show schedule
      if (profile.mode === 'auto' && profile.programs && profile.programs.length > 0) {
        return renderLightAutoSchedule(device, deviceConfig);
      }
    }
  }

  // Fallback: show simple connection state
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
 * Render light auto mode schedule display
 */
function renderLightAutoSchedule(device: DeviceStatus & { address: string }, deviceConfig: any): string {
  const programs = getDeviceAutoPrograms(device.address) as (AutoProgram & { status: string })[];
  
  if (programs.length === 0) {
    return `
      <div style="padding: 16px; text-align: center; color: var(--gray-500);">
        No auto programs configured
      </div>
    `;
  }

  // Define the sort order for statuses
  const statusOrder: { [key: string]: number } = {
    current: 0,
    next: 1,
    upcoming: 2,
    disabled: 3,
  };

  // Sort programs based on the new status field from the backend
  const sortedSchedules = [...programs].sort((a, b) => {
    const orderA = statusOrder[a.status] ?? 99;
    const orderB = statusOrder[b.status] ?? 99;
    if (orderA !== orderB) {
      return orderA - orderB;
    }
    // Fallback to sorting by sunrise time if statuses are the same
    return a.sunrise.localeCompare(b.sunrise);
  });

  // Filter out disabled programs and take the top 3 for display
  const topThree = sortedSchedules.filter(s => s.status !== 'disabled').slice(0, 3);

  return `
    <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
      ${topThree.length > 0 ? `
        <div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${topThree.map(p => renderScheduleItem(p)).join('')}
          </div>
        </div>
      ` : `
        <div style="text-align: center; color: var(--gray-500); font-size: 13px;">
          No scheduled programs
        </div>
      `}
    </div>
  `;
}

/**
 * Render a single schedule item with color coding
 */
function renderScheduleItem(program: AutoProgram & { status: string, channels?: any[] }): string {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'current': return 'var(--success)'; // Green
      case 'next': 
      case 'upcoming': return 'var(--primary)'; // Blue
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

  const accentColor = getStatusColor(program.status);
  const statusText = getStatusText(program.status);

  // Format channel levels in the order specified by device channels configuration
  let channelLevels = '';
  if (program.channels && Array.isArray(program.channels)) {
    // Use the device channel order with proper labels
    const levelStrings = program.channels
      .map(channel => {
        const value = program.levels[channel.key];
        // Use label if available, otherwise fallback to key
        const displayName = channel.label || channel.key.charAt(0).toUpperCase() + channel.key.slice(1);
        return `${displayName}:${value}%`;
      })
      .filter(str => str); // Filter out undefined values
    channelLevels = levelStrings.join(' '); // Single space between channels
  } else {
    // Fallback to alphabetical sorting if channels not provided
    channelLevels = Object.entries(program.levels)
      .map(([channel, value]) => {
        const displayName = channel.charAt(0).toUpperCase() + channel.slice(1);
        return `${displayName}:${value}%`;
      })
      .join(' '); // Single space between channels
  }

  const timeRange = `${program.sunrise} - ${program.sunset}`;

  return `
    <div style="padding: 8px 12px; background: var(--bg-primary); border-radius: 4px; border-left: 3px solid ${accentColor};">
      <div style="flex: 1; min-width: 0;">
        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">${program.label}</div>
        <div style="font-size: 11px; color: var(--text-secondary);">
          ${statusText} • ${timeRange} • ${program.rampMinutes}min ramp
        </div>
        <pre style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; margin: 0; padding: 0; font-family: 'Courier New', Courier, monospace; background: transparent; border: none; white-space: pre-wrap; word-wrap: break-word;">
${channelLevels}</pre>
      </div>
    </div>
  `;
}
