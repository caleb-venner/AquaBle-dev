/**
 * Device Configuration Modal - General device settings (nickname, auto-connect, etc.)
 * Separate from the device commands/settings modal
 */

import { deviceStore } from "../../../stores/deviceStore";
import { updateDeviceNaming, updateDeviceSettings, getDeviceConfiguration } from "../../../api/configurations";
import { showImportExportModal } from "./import-export-modal";

type DeviceMetadata = {
  id: string;
  name?: string;
  autoReconnect?: boolean;
  headNames?: Record<number, string>; // Doser only
  createdAt?: string;
  updatedAt?: string;
};

/**
 * Show the device configuration modal (general settings only)
 */
export async function showDeviceConfigModal(address: string, deviceType: 'doser' | 'light'): Promise<void> {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';

  // Get current device status
  const state = deviceStore.getState();
  const deviceStatus = state.devices.get(address)?.status;
  if (!deviceStatus) {
    console.error('Device not found:', address);
    return;
  }

  // Load device configuration (includes naming metadata)
  let metadata: DeviceMetadata | null = null;
  try {
    const config = await getDeviceConfiguration(address);
    metadata = {
      id: config.id,
      name: config.name,
      autoReconnect: config.autoReconnect,
      headNames: (config as any).headNames,
      createdAt: config.createdAt,
      updatedAt: config.updatedAt,
    };
  } catch (error) {
    console.error('Failed to load device configuration:', error);
  }

  // Get display name (metadata name or address)
  const displayName = metadata?.name || address;

  modal.innerHTML = `
    <div class="modal-content device-config-modal" style="max-width: 600px; max-height: 90vh; overflow-y: auto;" data-device-id="${address}" data-device-type="${deviceType}">
      <div class="modal-header">
        <h2>Device Configuration: ${displayName}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove();">×</button>
      </div>

      <div class="modal-body">
        ${renderGeneralSettingsForm(address, deviceType, metadata)}
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });

  // Setup save handler
  (window as any).saveDeviceConfig = async () => {
    await handleSaveConfig(address, deviceType, modal);
  };

  // Setup import/export handler
  (window as any).showImportExportModal = async (addr: string, type: 'doser' | 'light') => {
    await showImportExportModal(addr, type);
  };
}

/**
 * Render the general settings form (no tabs - just the config form)
 */
function renderGeneralSettingsForm(
  address: string,
  deviceType: 'doser' | 'light',
  metadata: DeviceMetadata | null
): string {
  const nickname = metadata?.name || '';
  const autoReconnect = metadata?.autoReconnect || false;

  return `
    <div class="settings-section">
      <h3>Device Information</h3>

      <div class="form-group">
        <label for="device-nickname">Device Nickname</label>
        <input
          type="text"
          id="device-nickname"
          class="form-control"
          value="${nickname}"
          placeholder="Device Name"
        />
        <small class="form-text">Custom name displayed in the interface</small>
      </div>

      <div class="form-group">
        <label class="checkbox-label">
          <input
            type="checkbox"
            id="auto-reconnect"
            ${autoReconnect ? 'checked' : ''}
          />
          <span>Auto Connect on Startup</span>
        </label>
        <small class="form-text">Automatically connect to this device when the service starts</small>
      </div>

      ${deviceType === 'doser' ? renderDoserHeadNames(metadata) : ''}

      <div class="form-actions">
        <button class="btn btn-primary" onclick="saveDeviceConfig()">
          Save Settings
        </button>
        <button class="btn btn-secondary" onclick="showImportExportModal('${address}', '${deviceType}')">
          Import/Export
        </button>
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove();">
          Cancel
        </button>
      </div>
    </div>
  `;
}

/**
 * Render doser-specific head names fields
 */
function renderDoserHeadNames(metadata: DeviceMetadata | null): string {
  const headNames = metadata?.headNames || {};

  return `
    <div class="form-group">
      <h4>Head Names</h4>
      <p class="form-text">Customize the names for each dosing head</p>

      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px;">
        ${[1, 2, 3, 4].map(headIndex => `
          <div>
            <label for="head-name-${headIndex}">Head ${headIndex}</label>
            <input
              type="text"
              id="head-name-${headIndex}"
              class="form-control"
              value="${headNames[headIndex] || ''}"
              placeholder="Head ${headIndex}"
            />
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/**
 * Handle saving device configuration
 */
async function handleSaveConfig(
  address: string,
  deviceType: 'doser' | 'light',
  modal: HTMLElement
): Promise<void> {
  try {
    // Collect form data
    const nickname = (document.getElementById('device-nickname') as HTMLInputElement)?.value || '';
    const autoReconnect = (document.getElementById('auto-reconnect') as HTMLInputElement)?.checked || false;

    const metadata: any = {
      id: address,
      name: nickname || undefined,
      autoReconnect
    };

    // Collect head names for dosers
    if (deviceType === 'doser') {
      const headNames: Record<number, string> = {};
      for (let i = 1; i <= 4; i++) {
        const input = document.getElementById(`head-name-${i}`) as HTMLInputElement;
        if (input && input.value.trim()) {
          headNames[i] = input.value.trim();
        }
      }
      if (Object.keys(headNames).length > 0) {
        metadata.headNames = headNames;
      }
    }

    // Save naming via unified API
    await updateDeviceNaming(address, {
      name: metadata.name,
      headNames: metadata.headNames,
    });

    // Save settings (autoReconnect) via separate endpoint
    await updateDeviceSettings(address, {
      autoReconnect: metadata.autoReconnect,
    });

    // Show success notification
    deviceStore.getState().actions.addNotification({
      type: 'success',
      message: 'Settings saved successfully'
    });

    // Refresh dashboard data (invalidate cache first to get fresh metadata)
    const { invalidateMetadataCache } = await import('../services/cache-service');
    invalidateMetadataCache();
    
    const { loadAllDashboardData } = await import('../services/data-service');
    await loadAllDashboardData();

    // Device card updater will automatically update the affected card
    // No need for full refreshDashboard() call

    // Close modal
    modal.remove();
  } catch (error) {
    console.error('Failed to save settings:', error);
    deviceStore.getState().actions.addNotification({
      type: 'error',
      message: `Failed to save settings: ${error instanceof Error ? error.message : 'Unknown error'}`
    });
  }
}
