/**
 * Device-specific utilities
 */

import { deviceStore } from "../../../stores/deviceStore";

/**
 * Get the configured name for a doser head
 */
export function getDoserHeadName(deviceAddress: string, headIndex: number): string | null {
  const state = deviceStore.getState();
  
  // Convert 0-based index to 1-based for metadata lookup
  const metadataIndex = headIndex + 1;
  
  // First try configurations
  const config = state.configurations.dosers.get(deviceAddress);
  if (config?.headNames && metadataIndex in config.headNames) {
    return config.headNames[metadataIndex];
  }
  
  // Then try device status metadata
  const device = state.devices.get(deviceAddress);
  if (device?.status?.metadata && 'headNames' in device.status.metadata && device.status.metadata.headNames) {
    return device.status.metadata.headNames[metadataIndex] || null;
  }
  
  return null;
}

/**
 * Get the lifetime total for a doser head
 */
export function getHeadLifetimeTotal(headIndex: number, deviceAddress?: string): string {
  if (!deviceAddress) return 'N/A';

  const state = deviceStore.getState();
  const device = state.devices.get(deviceAddress);
  const parsed = device?.status?.parsed as any;

  if (!parsed || !parsed.lifetime_totals_tenths_ml || !Array.isArray(parsed.lifetime_totals_tenths_ml)) {
    return 'N/A';
  }

  // Convert 1-based index to 0-based for array access
  const lifetimeTotal = parsed.lifetime_totals_tenths_ml[headIndex - 1];

  if (typeof lifetimeTotal !== 'number') {
    return 'N/A';
  }

  // Convert tenths of mL to mL and format appropriately
  const totalMl = lifetimeTotal / 10;

  if (totalMl >= 1000) {
    return `${(totalMl / 1000).toFixed(2)}L`;
  }

  return `${totalMl.toFixed(1)}ml`;
}

/**
 * Format schedule days for display
 */
export function formatScheduleDays(weekdays: number[] | undefined): string {
  if (!weekdays || !Array.isArray(weekdays) || weekdays.length === 0) {
    return 'None';
  }

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const validDays = weekdays.filter(day => typeof day === 'number' && day >= 0 && day <= 6);

  if (validDays.length === 0) {
    return 'None';
  }

  const sortedDays = [...validDays].sort();

  // Check for everyday (all 7 days)
  if (sortedDays.length === 7) {
    return 'Everyday';
  }

  // Check for weekdays (Mon-Fri)
  if (sortedDays.length === 5 && sortedDays.every(day => day >= 1 && day <= 5)) {
    return 'Weekdays';
  }

  // Check for weekends (Sat-Sun)
  if (sortedDays.length === 2 && sortedDays.includes(0) && sortedDays.includes(6)) {
    return 'Weekends';
  }

  // Otherwise, list the days
  return sortedDays.map(day => dayNames[day]).join(', ');
}

/**
 * Get configuration data for a specific head
 */
export function getHeadConfigData(headIndex: number, deviceAddress: string): { setDose: string; schedule: string } {
  const state = deviceStore.getState();
  const savedConfigs = Array.from(state.configurations.dosers.values());
  const savedConfig = savedConfigs.find((config: any) => config.id === deviceAddress);

  if (!savedConfig || !savedConfig.configurations || savedConfig.configurations.length === 0) {
    return { setDose: 'N/A', schedule: 'N/A' };
  }

  const activeConfig = savedConfig.configurations.find((c: any) => c.id === savedConfig.activeConfigurationId);
  if (!activeConfig || !activeConfig.revisions || activeConfig.revisions.length === 0) {
    return { setDose: 'N/A', schedule: 'N/A' };
  }

  const latestRevision = activeConfig.revisions[activeConfig.revisions.length - 1];
  const configHead = latestRevision.heads?.find((h: any) => h.index === headIndex);

  if (!configHead) {
    return { setDose: 'N/A', schedule: 'N/A' };
  }

  // Show configuration data even if head is not currently active on device
  // This ensures configured heads always display their settings
  let setDose = 'N/A';
  const schedule = configHead.schedule;
  if (schedule) {
    // Format dose amount
    if (schedule.volume_ml !== undefined && schedule.volume_ml !== null) {
      setDose = `${schedule.volume_ml}ml`;
    } else if (schedule.volume_tenths_ml !== undefined && schedule.volume_tenths_ml !== null) {
      setDose = `${schedule.volume_tenths_ml / 10}ml`;
    }

    // Format schedule days
    const scheduleText = formatScheduleDays(configHead.recurrence?.days);
    return { setDose, schedule: scheduleText };
  }

  return { setDose: 'N/A', schedule: 'N/A' };
}
