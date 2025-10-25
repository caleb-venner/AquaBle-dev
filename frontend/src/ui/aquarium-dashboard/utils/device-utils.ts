/**
 * Device-specific utilities
 */

import { deviceStore } from "../../../stores/deviceStore";

/**
 * Get the configured name for a doser head
 */
export function getDoserHeadName(deviceAddress: string, headIndex: number): string | null {
  const state = deviceStore.getState();
  
  // headIndex is 1-based (1-4)
  const config = state.configurations.dosers.get(deviceAddress);
  if (config?.headNames && headIndex in config.headNames) {
    return config.headNames[headIndex];
  }
  
  return null;
}

/**
 * Get the lifetime total for a doser head
 * Note: With ultra-minimal DeviceStatus, parsed data is no longer in status.
 * This would need to fetch from configuration API if needed.
 */
export function getHeadLifetimeTotal(headIndex: number, deviceAddress?: string): string {
  // Ultra-minimal DeviceStatus no longer includes parsed data
  // Lifetime totals would need to be fetched from device configuration API
  return 'N/A';
}

/**
 * Format schedule days for display
 */
export function formatScheduleDays(weekdays: number[] | string[] | undefined): string {
  if (!weekdays || !Array.isArray(weekdays) || weekdays.length === 0) {
    return 'None';
  }

  // If weekdays are strings (e.g., 'monday', 'tuesday'), convert to abbreviations
  if (typeof weekdays[0] === 'string') {
    const dayMap: Record<string, string> = {
      'monday': 'Mon',
      'tuesday': 'Tue',
      'wednesday': 'Wed',
      'thursday': 'Thu',
      'friday': 'Fri',
      'saturday': 'Sat',
      'sunday': 'Sun'
    };
    const abbrevDays = (weekdays as string[]).map(day => dayMap[day.toLowerCase()]).filter(Boolean);
    
    if (abbrevDays.length === 7) return 'Everyday';
    if (abbrevDays.length === 5 && ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].every(d => abbrevDays.includes(d))) {
      return 'Weekdays';
    }
    if (abbrevDays.length === 2 && abbrevDays.includes('Sat') && abbrevDays.includes('Sun')) {
      return 'Weekends';
    }
    return abbrevDays.join(', ');
  }

  // If weekdays are numbers (0-6 indices), handle as before
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const validDays = (weekdays as number[]).filter(day => typeof day === 'number' && day >= 0 && day <= 6);

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
  const config = state.configurations.dosers.get(deviceAddress);

  if (!config || !config.configurations || config.configurations.length === 0) {
    return { setDose: 'N/A', schedule: 'N/A' };
  }

  const activeConfig = config.configurations.find((c: any) => c.id === config.activeConfigurationId) || config.configurations[0];
  if (!activeConfig || !activeConfig.revisions || activeConfig.revisions.length === 0) {
    return { setDose: 'N/A', schedule: 'N/A' };
  }

  const latestRevision = activeConfig.revisions[activeConfig.revisions.length - 1];
  const configHead = latestRevision.heads?.find((h: any) => h.index === headIndex);

  if (!configHead) {
    return { setDose: 'N/A', schedule: 'N/A' };
  }

  // Extract dose from schedule
  let setDose = 'N/A';
  const schedule = configHead.schedule;
  if (schedule && schedule.dailyDoseMl !== undefined && schedule.dailyDoseMl !== null) {
    setDose = `${schedule.dailyDoseMl}ml`;
  }

  // Format schedule days from recurrence
  const scheduleText = formatScheduleDays(configHead.recurrence?.days);
  return { setDose, schedule: scheduleText };
}
