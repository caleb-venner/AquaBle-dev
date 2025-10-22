/**
 * Modal components for device configuration - Visual rendering only
 */

import type { DoserDevice, LightDevice } from "../../../types/models";
import { executeCommand } from "../../../api/commands";
import type { CommandRequest } from "../../../types/models";
import { getDeviceChannelNames } from "../../../utils";
import { deviceStore } from "../../../stores/deviceStore";

/**
 * Show the doser device settings modal - for commands and schedules (visual only)
 */
export function showDoserDeviceSettingsModal(device: DoserDevice): void {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';

  modal.innerHTML = `
    <div class="modal-content doser-config-modal" style="max-width: 1000px; max-height: 90vh; overflow-y: auto;" data-device-id="${device.id}">
      <div class="modal-header">
        <h2>Doser Settings: ${device.name || device.id}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove();">×</button>
      </div>
      <div class="modal-body">
        ${renderDoserDeviceSettingsInterface(device)}
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Make selectDoseHead globally available for onclick handlers
  (window as any).selectDoseHead = selectDoseHead;

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

/**
 * Show the light device settings modal - for commands and controls (visual only)
 */
export function showLightDeviceSettingsModal(device: LightDevice): void {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';

  modal.innerHTML = `
    <div class="modal-content light-settings-modal" style="max-width: 900px; max-height: 90vh; overflow-y: auto;" data-device-id="${device.id}" data-address="${device.id}">
      <div class="modal-header">
        <h2>Light Settings: ${device.name || device.id}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove();">×</button>
      </div>
      <div class="modal-body">
        ${renderLightDeviceSettingsInterface(device)}
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Store device object on modal element for tab switching
  const modalContent = modal.querySelector('.modal-content') as any;
  if (modalContent) {
    modalContent._deviceData = device;
  }

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

/**
 * Render the doser device settings interface (visual only)
 */
function renderDoserDeviceSettingsInterface(device: DoserDevice): string {
  return `
    <div class="doser-config-interface">
      <!-- Head Selector Section -->
      <div class="config-section">
        <h3>Dosing Heads</h3>
        <p class="section-description">Select a head to configure its schedule and settings.</p>

        <div class="heads-grid">
          ${renderHeadSelector(device)}
        </div>
      </div>

      <!-- Command Interface Section -->
      <div class="config-section">
        <div id="command-interface">
          <div class="no-head-selected">
            <h4>No Head Selected</h4>
            <p>Select a dosing head above to configure its schedule and settings.</p>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove();">
          Close
        </button>
      </div>
    </div>
  `;
}

/**
 * Render the 4-head visual selector as individual cards
 */
function renderHeadSelector(device: DoserDevice): string {
  // Ensure we have all 4 heads
  const allHeads = [];
  for (let i = 1; i <= 4; i++) {
    const existingHead = device.heads?.find((h) => h.index === i);
    const headName = `Head ${i}`;

    allHeads.push(existingHead || {
      index: i as 1|2|3|4,
      label: headName,
      active: false,
      schedule: { mode: 'single' as const, dailyDoseMl: 10.0, startTime: '09:00' },
      recurrence: { days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] },
      missedDoseCompensation: false,
      calibration: { mlPerSecond: 1.0, lastCalibratedAt: new Date().toISOString() }
    });
  }

  return `
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
      ${allHeads.map(head => renderDoseHeadCard(head)).join('')}
    </div>
  `;
}

/**
 * Render a single dose head card
 */
function renderDoseHeadCard(head: any): string {
  const headName = head.label || `Head ${head.index}`;
  const statusText = head.active ? 'Active' : 'Disabled';
  const statusColor = head.active ? 'var(--success)' : 'var(--gray-400)';
  const modeText = getModeText(head.schedule?.mode);

  return `
    <div class="dose-head-card ${head.active ? 'active' : 'inactive'}" style="background: white; border: 1px solid var(--gray-200); border-radius: 8px; padding: 16px; cursor: pointer; transition: all 0.2s ease;" onclick="selectDoseHead(${head.index})">
      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
        <div>
          <div style="font-size: 16px; font-weight: 600; color: var(--gray-900); margin-bottom: 4px;">${headName}</div>
          <div style="font-size: 13px; color: var(--gray-500);">${modeText}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 12px; color: ${statusColor}; font-weight: 600; padding: 4px 8px; background: ${statusColor}20; border-radius: 12px;">${statusText}</div>
        </div>
      </div>

      ${head.active ? `
        <div style="margin-bottom: 12px;">
          <div style="font-size: 13px; color: var(--gray-700); margin-bottom: 4px;">
            ${head.schedule?.mode === 'single' ?
              `Daily dose: ${head.schedule.dailyDoseMl || 0}ml at ${head.schedule.startTime || '00:00'}` :
              head.schedule?.mode === 'every_hour' ?
              `24H mode: ${head.schedule.dailyDoseMl || 0}ml total` :
              `Custom schedule configured`
            }
          </div>
        </div>
      ` : ''}

      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 12px; color: var(--gray-500);">
          ${head.recurrence?.days?.length === 7 ? 'Daily' : `${head.recurrence?.days?.length || 0} days/week`}
        </div>
        <div style="font-size: 12px; color: var(--primary); font-weight: 500;">
          Configure →
        </div>
      </div>
    </div>
  `;
}

/**
 * Get mode text for display
 */
function getModeText(mode?: string): string {
  switch (mode) {
    case 'single': return 'Daily Dose';
    case 'every_hour': return '24 Hour';
    case 'custom_periods': return 'Custom Periods';
    case 'timer': return 'Timer';
    default: return 'Disabled';
  }
}

/**
 * Handle dose head selection
 */
function selectDoseHead(headIndex: number): void {
  // Find the modal and update the command interface
  const modal = document.querySelector('.doser-config-modal') as HTMLElement;
  if (!modal) return;

  const commandInterface = modal.querySelector('#command-interface') as HTMLElement;
  if (!commandInterface) return;

  // Get the device data from the modal
  const deviceId = modal.getAttribute('data-device-id');
  if (!deviceId) return;

  // For now, create a mock head object - in a real implementation this would come from the device data
  const mockHead = {
    index: headIndex,
    label: `Head ${headIndex}`,
    active: true,
    schedule: { mode: 'single' as const, dailyDoseMl: 10.0, startTime: '09:00' },
    recurrence: { days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] },
    missedDoseCompensation: false,
    calibration: { mlPerSecond: 1.0, lastCalibratedAt: new Date().toISOString() }
  };

  // Update the command interface
  commandInterface.innerHTML = renderHeadCommandInterface(headIndex, mockHead, deviceId);

  // Update card selection states
  const cards = modal.querySelectorAll('.dose-head-card');
  cards.forEach((card, index) => {
    if (index === headIndex - 1) {
      card.classList.add('selected');
    } else {
      card.classList.remove('selected');
    }
  });
}

/**
 * Render the light device settings interface with tabs for Manual/Auto modes
 */
function renderLightDeviceSettingsInterface(device: LightDevice): string {
  return `
    <div class="light-config-interface">
      <!-- Tab Navigation -->
      <div class="modal-tabs">
        <button class="tab-button active" onclick="switchLightSettingsTab('manual')">
          Manual Mode
        </button>
        <button class="tab-button" onclick="switchLightSettingsTab('auto')">
          Auto Mode
        </button>
      </div>

      <!-- Tab Content -->
      <div id="light-settings-tab-content">
        ${renderLightManualModeTab(device)}
      </div>
    </div>
  `;
}

/**
 * Render Manual Mode tab content
 */
function renderLightManualModeTab(device: LightDevice): string {
  // Get channel names from device configuration
  const zustandState = deviceStore.getState();
  const lightConfig = zustandState.configurations.lights.get(device.id);
  const channelNames = lightConfig?.channels?.map((ch: any) => ch.label) || ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'];

  return `
    <div class="settings-section">
      <h3>Manual Brightness Control</h3>
      <p>Set individual channel brightness levels (device will switch to manual mode)</p>

      <div class="channel-controls">
        ${channelNames.map((channelName, index) => `
          <div class="form-group">
            <label for="manual-channel-${index}">${channelName}</label>
            <input
              type="number"
              id="manual-channel-${index}"
              min="0"
              max="100"
              value="50"
              class="form-control"
            />
          </div>
        `).join('')}
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" onclick="sendLightManualModeCommand('${device.id}')">
          Send Command
        </button>
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove();">
          Close
        </button>
      </div>
    </div>
  `;
}

/**
 * Render Auto Mode tab content
 */
function renderLightAutoModeTab(device: LightDevice): string {
  // Get channel names from device configuration
  const zustandState = deviceStore.getState();
  const lightConfig = zustandState.configurations.lights.get(device.id);
  const channelNames = lightConfig?.channels?.map((ch: any) => ch.label) || ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'];
  const channelCount = channelNames.length;

  // Determine grid layout based on channel count
  let gridClass = '';
  let channelsPerRow = 1;

  if (channelCount === 1) {
    gridClass = 'channel-grid-1';
    channelsPerRow = 1;
  } else if (channelCount === 3) {
    gridClass = 'channel-grid-3';
    channelsPerRow = 3;
  } else if (channelCount === 4) {
    gridClass = 'channel-grid-2x2';
    channelsPerRow = 2;
  } else {
    // Default fallback for other counts
    gridClass = 'channel-grid-default';
    channelsPerRow = Math.min(channelCount, 3);
  }

  return `
    <div class="settings-section">
      <h3>Auto Mode Schedule</h3>
      <p>Configure sunrise/sunset times and brightness levels (device will switch to auto mode)</p>

      <div class="form-group">
        <label for="schedule-label">Schedule Label</label>
        <input
          type="text"
          id="schedule-label"
          class="form-control"
          placeholder="e.g., Morning Schedule, Weekend Lighting"
          maxlength="50"
        />
        <small class="form-text">Optional: Give this schedule a descriptive name</small>
      </div>

      <div class="time-controls-row">
        <div class="form-group">
          <label for="sunrise-time">Sunrise Time (24h)</label>
          <input
            type="time"
            id="sunrise-time"
            class="form-control"
            value="08:00"
          />
        </div>

        <div class="form-group">
          <label for="sunset-time">Sunset Time (24h)</label>
          <input
            type="time"
            id="sunset-time"
            class="form-control"
            value="20:00"
          />
        </div>

        <div class="form-group">
          <label for="ramp-time">Ramp Time (minutes)</label>
          <input
            type="number"
            id="ramp-time"
            class="form-control"
            value="60"
            min="1"
            max="300"
          />
        </div>
      </div>

      <div class="form-group">
        <label>Active Days:</label>
        <div class="weekday-selector">
          ${[
            { name: 'monday', label: 'Mon' },
            { name: 'tuesday', label: 'Tue' },
            { name: 'wednesday', label: 'Wed' },
            { name: 'thursday', label: 'Thu' },
            { name: 'friday', label: 'Fri' },
            { name: 'saturday', label: 'Sat' },
            { name: 'sunday', label: 'Sun' }
          ].map(day => `
            <label class="weekday-option">
              <input type="checkbox" value="${day.name}" checked id="weekday-auto-${day.name}">
              <span class="weekday-label">${day.label}</span>
            </label>
          `).join('')}
        </div>
      </div>

      <h4>Peak Brightness Levels</h4>
      <div class="channel-controls ${gridClass}">
        ${channelNames.map((channelName, index) => `
          <div class="form-group channel-item">
            <label for="auto-channel-${index}">${channelName}</label>
            <input
              type="number"
              id="auto-channel-${index}"
              min="0"
              max="100"
              value="50"
              class="form-control"
            />
          </div>
        `).join('')}
      </div>

      <div class="form-group">
        <button class="btn btn-danger" onclick="sendLightResetAutoModeCommand('${device.id}')">
          Reset Auto Mode Settings
        </button>
        <small class="form-text">This will reset all auto mode settings to factory defaults</small>
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" onclick="sendLightAutoModeCommand('${device.id}')">
          Send Command
        </button>
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove();">
          Close
        </button>
      </div>
    </div>
  `;
}

/**
 * Render the command interface for a selected head (visual only)
 */
export function renderHeadCommandInterface(headIndex: number, head: any, deviceId: string): string {
  const schedule = head.schedule || { mode: 'single', dailyDoseMl: 10.0, startTime: '09:00' };
  const recurrence = head.recurrence || { days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] };

  return `
    <div class="head-command-interface">
      <div class="command-header">
        <h4>Configure Head ${headIndex}</h4>
        <div class="head-status-indicator ${head.active ? 'active' : 'inactive'}">
          ${head.active ? 'Active' : 'Inactive'}
        </div>
      </div>

      <!-- Schedule Configuration -->
      <div class="form-section">
        <h5>Schedule Configuration</h5>

        <div class="form-group">
          <label for="schedule-mode-${headIndex}">Mode:</label>
          <select id="schedule-mode-${headIndex}" class="form-select">
            <option value="disabled" ${!head.active ? 'selected' : ''}>Disabled</option>
            <option value="single" ${schedule.mode === 'single' ? 'selected' : ''}>Daily - Single dose at set time</option>
            <option value="every_hour" ${schedule.mode === 'every_hour' ? 'selected' : ''}>24 Hour - Hourly dosing</option>
            <option value="custom_periods" ${schedule.mode === 'custom_periods' ? 'selected' : ''}>Custom - Custom time periods</option>
            <option value="timer" ${schedule.mode === 'timer' ? 'selected' : ''}>Timer - Multiple specific times</option>
          </select>
        </div>

        <div id="schedule-details-${headIndex}">
          ${renderScheduleDetails(headIndex, schedule)}
        </div>

        <div class="form-group">
          <label>Active Days:</label>
          <div class="weekday-selector">
            ${[
              { name: 'monday', label: 'Mon' },
              { name: 'tuesday', label: 'Tue' },
              { name: 'wednesday', label: 'Wed' },
              { name: 'thursday', label: 'Thu' },
              { name: 'friday', label: 'Fri' },
              { name: 'saturday', label: 'Sat' },
              { name: 'sunday', label: 'Sun' }
            ].map(day => `
              <label class="weekday-option">
                <input type="checkbox" value="${day.name}"
                       ${recurrence.days.includes(day.name) ? 'checked' : ''}
                       id="weekday-${headIndex}-${day.name}">
                <span class="weekday-label">${day.label}</span>
              </label>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- Command Actions -->
      <div class="command-actions">
        <button class="btn btn-success btn-large" onclick="sendDoserScheduleCommand('${deviceId}', ${headIndex})">
          Send Command
        </button>
      </div>
    </div>
  `;
}

/**
 * Render schedule details based on mode (visual only)
 */
function renderScheduleDetails(headIndex: number, schedule: any): string {
  switch (schedule.mode) {
    case 'single':
      return `
        <div class="schedule-single">
          <div class="schedule-mode-description">
            <p><strong>Daily Mode:</strong> Dose once per day at a specific time</p>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="dose-amount-${headIndex}">Dose Amount (ml):</label>
              <input type="number" id="dose-amount-${headIndex}"
                     value="${schedule.dailyDoseMl || 10}"
                     min="0.1" max="6553.5" step="0.1" class="form-input">
            </div>
            <div class="form-group">
              <label for="dose-time-${headIndex}">Time:</label>
              <input type="time" id="dose-time-${headIndex}"
                     value="${schedule.startTime || '09:00'}"
                     class="form-input">
            </div>
          </div>
        </div>
      `;

    case 'every_hour':
      return `
        <div class="schedule-every-hour">
          <div class="schedule-mode-description">
            <p><strong>24 Hour Mode:</strong> Dose every hour starting at a specific time</p>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="daily-total-${headIndex}">Total Daily Amount (ml):</label>
              <input type="number" id="daily-total-${headIndex}"
                     value="${schedule.dailyDoseMl || 24}"
                     min="0.1" max="6553.5" step="0.1" class="form-input">
            </div>
            <div class="form-group">
              <label for="start-time-${headIndex}">Start Time:</label>
              <input type="time" id="start-time-${headIndex}"
                     value="${schedule.startTime || '08:00'}"
                     class="form-input">
            </div>
          </div>
          <div class="hourly-info">
            <p>Hourly dose: <span id="hourly-dose-${headIndex}">${((schedule.dailyDoseMl || 24) / 24).toFixed(1)}ml</span></p>
          </div>
        </div>
      `;

    default:
      return '<div class="schedule-disabled"><p>Head is disabled. Select a mode to configure.</p></div>';
  }
}

/**
 * Switch between Manual and Auto mode tabs for light settings
 */
function switchLightSettingsTab(mode: 'manual' | 'auto'): void {
  console.log('switchLightSettingsTab called with mode:', mode);

  const tabs = document.querySelectorAll('.modal-tabs .tab-button');
  const contentContainer = document.getElementById('light-settings-tab-content');

  if (!contentContainer) {
    console.error('Content container not found');
    return;
  }

  // Update tab button active states
  tabs.forEach(tab => {
    tab.classList.remove('active');
  });

  const activeTab = Array.from(tabs).find(tab =>
    tab.textContent?.toLowerCase().includes(mode)
  );
  if (activeTab) {
    activeTab.classList.add('active');
  }

  // Get device data from modal element (stored when modal was created)
  const modal = document.querySelector('.modal-content.light-settings-modal') as any;
  if (!modal) {
    console.error('Modal element not found');
    return;
  }

  const device = modal._deviceData;
  if (!device) {
    console.error('Device data not found on modal element');
    return;
  }

  console.log('Rendering tab for mode:', mode);

  // Render appropriate tab content
  contentContainer.innerHTML = mode === 'manual'
    ? renderLightManualModeTab(device)
    : renderLightAutoModeTab(device);

  console.log('Tab content updated');
}

/**
 * Send manual mode command to light device
 */
async function sendLightManualModeCommand(address: string): Promise<void> {
  try {
    // Get channel values from number inputs
    const channelElements = document.querySelectorAll<HTMLInputElement>('[id^="manual-channel-"]');
    const channelValues = Array.from(channelElements).map(el => parseInt(el.value, 10));

    console.log('Sending manual mode commands:', { address, channelValues });

    // Validate channel values
    if (channelValues.some(v => isNaN(v) || v < 0 || v > 100)) {
      alert('Please enter valid brightness values (0-100) for all channels');
      return;
    }

    // Send individual set_brightness commands for each channel (switches to manual mode)
    let lastResult = null;
    for (let colorIndex = 0; colorIndex < channelValues.length; colorIndex++) {
      const request: CommandRequest = {
        action: 'set_brightness',
        args: {
          brightness: channelValues[colorIndex],
          color: colorIndex
        },
        timeout: 15.0
      };

      console.log(`Sending brightness command for channel ${colorIndex}:`, request);
      lastResult = await executeCommand(address, request);

      if (lastResult.status === 'failed') {
        alert(`Channel ${colorIndex} command failed: ${lastResult.error || 'Unknown error'}`);
        return;
      }
    }

    if (lastResult?.status === 'success') {
      alert('Manual brightness set successfully! Device switched to manual mode.');
    } else {
      alert(`Final command status: ${lastResult?.status || 'unknown'}`);
    }

  } catch (error) {
    console.error('Failed to send manual mode commands:', error);
    alert(`Failed to send command: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Send auto mode command to light device
 */
async function sendLightAutoModeCommand(address: string): Promise<void> {
  try {
    const scheduleLabel = (document.getElementById('schedule-label') as HTMLInputElement)?.value.trim();
    const sunriseTime = (document.getElementById('sunrise-time') as HTMLInputElement)?.value;
    const sunsetTime = (document.getElementById('sunset-time') as HTMLInputElement)?.value;
    const rampTime = parseInt((document.getElementById('ramp-time') as HTMLInputElement)?.value || '60', 10);

    // Get channel values from number inputs
    const channelElements = document.querySelectorAll<HTMLInputElement>('[id^="auto-channel-"]');
    const channelValues = Array.from(channelElements).map(el => parseInt(el.value, 10));

    // Get active days from checkboxes (already in lowercase full name format)
    const dayCheckboxes = document.querySelectorAll<HTMLInputElement>('[id^="weekday-auto-"]');
    const weekdays = Array.from(dayCheckboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value);

    console.log('Sending auto mode command:', {
      address,
      scheduleLabel,
      sunriseTime,
      sunsetTime,
      rampTime,
      channelValues,
      weekdays
    });

    // Validation
    if (!sunriseTime || !sunsetTime) {
      alert('Please enter both sunrise and sunset times');
      return;
    }

    if (channelValues.some(v => isNaN(v) || v < 0 || v > 100)) {
      alert('Please enter valid brightness values (0-100) for all channels');
      return;
    }

    if (weekdays.length === 0) {
      alert('Please select at least one active day');
      return;
    }

    // Build channel brightness dict (assuming Red, Green, Blue, White order)
    const channelNames = ['red', 'green', 'blue', 'white'];
    const channels: { [key: string]: number } = {};
    channelNames.forEach((name, index) => {
      if (index < channelValues.length) {
        channels[name] = channelValues[index];
      }
    });

    // Send command to add auto setting
    const request: CommandRequest = {
      action: 'add_auto_setting',
      args: {
        sunrise: sunriseTime,
        sunset: sunsetTime,
        channels: channels,
        ramp_up_minutes: rampTime,
        weekdays: weekdays,
        ...(scheduleLabel && { label: scheduleLabel })  // Include label only if provided
      },
      timeout: 20.0
    };

    const result = await executeCommand(address, request);

    if (result.status === 'success') {
      alert('Auto mode schedule set successfully! Device configured for auto mode.');
    } else if (result.status === 'failed') {
      alert(`Command failed: ${result.error || 'Unknown error'}`);
    } else {
      alert(`Command status: ${result.status}`);
    }

  } catch (error) {
    console.error('Failed to send auto mode command:', error);
    alert(`Failed to send command: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Send reset auto mode command to light device
 */
async function sendLightResetAutoModeCommand(address: string): Promise<void> {
  try {
    const confirmed = confirm('Are you sure you want to reset all auto mode settings to factory defaults? This cannot be undone.');
    if (!confirmed) return;

    console.log('Sending reset auto mode command:', { address });

    const result = await executeCommand(address, {
      action: 'reset_auto_settings',
      args: {}
    });

    console.log('Reset command result:', result);

    if (result.status === 'success') {
      alert('Auto mode settings reset successfully');
    } else {
      alert(`Reset failed: ${result.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Failed to send reset command:', error);
    alert('Failed to reset auto mode settings. Check console for details.');
  }
}

/**
 * Send doser schedule command to device
 */
async function sendDoserScheduleCommand(address: string, headIndex: number): Promise<void> {
  try {
    console.log('Sending doser schedule command:', { address, headIndex });

    // Get form values
    const doseAmountInput = document.getElementById(`dose-amount-${headIndex}`) as HTMLInputElement;
    const doseTimeInput = document.getElementById(`dose-time-${headIndex}`) as HTMLInputElement;

    if (!doseAmountInput || !doseTimeInput) {
      alert('Form inputs not found. Please refresh the page and try again.');
      return;
    }

    const doseAmount = parseFloat(doseAmountInput.value);
    const doseTime = doseTimeInput.value;

    if (isNaN(doseAmount) || doseAmount <= 0) {
      alert('Please enter a valid dose amount greater than 0.');
      return;
    }

    if (!doseTime) {
      alert('Please select a dose time.');
      return;
    }

    // Parse time
    const [hourStr, minuteStr] = doseTime.split(':');
    const hour = parseInt(hourStr, 10);
    const minute = parseInt(minuteStr, 10);

    // Get selected weekdays (already in lowercase full name format)
    const weekdayCheckboxes = document.querySelectorAll(`input[id^="weekday-${headIndex}-"]:checked`);
    const weekdays = Array.from(weekdayCheckboxes).map(cb => (cb as HTMLInputElement).value);

    // Convert dose amount to tenths of ml (backend expects integer)
    const volumeTenthsMl = Math.round(doseAmount * 10);

    const args = {
      head_index: headIndex - 1, // Backend uses 0-based indexing
      volume_tenths_ml: volumeTenthsMl,
      hour,
      minute,
      weekdays: weekdays.length > 0 ? weekdays : undefined
    };

    console.log('Command args:', args);

    const result = await executeCommand(address, {
      action: 'set_schedule',
      args
    });

    console.log('Doser schedule command result:', result);

    if (result.status === 'success') {
      alert(`Schedule set successfully for Head ${headIndex}!`);
    } else {
      alert(`Schedule command failed: ${result.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Failed to send doser schedule command:', error);
    alert('Failed to set schedule. Check console for details.');
  }
}

// Attach global functions for UI interactions
(window as any).selectDoseHead = selectDoseHead;
(window as any).switchLightSettingsTab = switchLightSettingsTab;
(window as any).sendLightManualModeCommand = sendLightManualModeCommand;
(window as any).sendLightAutoModeCommand = sendLightAutoModeCommand;
(window as any).sendLightResetAutoModeCommand = sendLightResetAutoModeCommand;
(window as any).sendDoserScheduleCommand = sendDoserScheduleCommand;
(window as any).showDoserDeviceSettingsModal = showDoserDeviceSettingsModal;
(window as any).showLightDeviceSettingsModal = showLightDeviceSettingsModal;
