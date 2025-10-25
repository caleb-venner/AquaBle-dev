/**
 * Import/Export Modal - Allows users to backup and restore device configurations
 */

import { deviceStore } from "../../../stores/deviceStore";
import { exportDeviceConfiguration, importDeviceConfiguration } from "../../../api/configurations";

type ExportData = {
  address: string;
  deviceType: 'doser' | 'light';
  config: any;
  exportedAt: string;
};

/**
 * Show the import/export modal for a device
 */
export async function showImportExportModal(address: string, deviceType: 'doser' | 'light'): Promise<void> {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';

  // Get current device status
  const state = deviceStore.getState();
  const deviceStatus = state.devices.get(address)?.status;
  if (!deviceStatus) {
    console.error('Device not found:', address);
    return;
  }

  const displayName = state.devices.get(address)?.configuration?.name || address;

  modal.innerHTML = `
    <div class="modal-content import-export-modal" style="max-width: 500px; max-height: 90vh; overflow-y: auto;" data-device-id="${address}" data-device-type="${deviceType}">
      <div class="modal-header">
        <h2>Import/Export Configuration</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove();">×</button>
      </div>

      <div class="modal-body">
        <div class="settings-section">
          <h3>Export Configuration</h3>
          <p style="color: #666; font-size: 0.9em; margin-bottom: 12px;">
            Download the current configuration as a JSON file. You can edit this file and import it back later.
          </p>
          <button class="btn btn-primary" onclick="window.handleExportConfig('${address}', '${deviceType}')">
            Download Configuration
          </button>
        </div>

        <hr style="margin: 24px 0; border: none; border-top: 1px solid #ddd;">

        <div class="settings-section">
          <h3>Import Configuration</h3>
          <p style="color: #666; font-size: 0.9em; margin-bottom: 12px;">
            Select a JSON file previously exported from this device. The current configuration will be replaced.
          </p>
          <div class="file-input-wrapper">
            <input
              type="file"
              id="config-file-input"
              accept=".json"
              style="display: none;"
              onchange="window.handleImportFile('${address}', '${deviceType}')"
            />
            <button class="btn btn-secondary" onclick="document.getElementById('config-file-input').click()">
              Choose File
            </button>
            <span id="file-name" style="margin-left: 12px; color: #666;"></span>
          </div>
          <div id="import-status" style="margin-top: 12px; display: none;">
            <div id="import-message" style="padding: 8px; border-radius: 4px;"></div>
          </div>
        </div>
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
}

/**
 * Handle exporting device configuration
 */
async function handleExportConfig(address: string, deviceType: 'doser' | 'light'): Promise<void> {
  try {
    // Show loading state
    const button = event?.currentTarget as HTMLButtonElement;
    const originalText = button?.textContent;
    if (button) button.textContent = 'Exporting...';
    if (button) button.disabled = true;

    // Get current configuration
    const config = await exportDeviceConfiguration(address);

    // Create export data object with metadata
    const exportData: ExportData = {
      address,
      deviceType,
      config,
      exportedAt: new Date().toISOString(),
    };

    // Create JSON blob and download
    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `${address.replace(/:/g, '-')}-config.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    if (button) {
      button.textContent = originalText;
      button.disabled = false;
    }

    console.log('Configuration exported successfully');
  } catch (error) {
    console.error('Export failed:', error);
    const button = event?.currentTarget as HTMLButtonElement;
    if (button) {
      button.textContent = 'Export failed';
      button.disabled = false;
      setTimeout(() => {
        button.textContent = 'Download Configuration';
      }, 3000);
    }
  }
}

/**
 * Handle importing device configuration from file
 */
async function handleImportFile(address: string, deviceType: 'doser' | 'light'): Promise<void> {
  try {
    const fileInput = document.getElementById('config-file-input') as HTMLInputElement;
    const file = fileInput?.files?.[0];
    if (!file) return;

    // Show file name
    const fileNameSpan = document.getElementById('file-name');
    if (fileNameSpan) {
      fileNameSpan.textContent = `Selected: ${file.name}`;
    }

    // Show status area
    const statusDiv = document.getElementById('import-status');
    if (statusDiv) {
      statusDiv.style.display = 'block';
      statusDiv.style.opacity = '0.5';
    }

    // Validate and read file
    const text = await file.text();
    let importData: any;
    try {
      importData = JSON.parse(text);
    } catch (e) {
      throw new Error('Invalid JSON format in file');
    }

    // Check if this looks like an exported config
    if (!importData.config || !importData.address) {
      throw new Error('File does not appear to be a valid AquaBle export');
    }

    // Confirm before overwriting
    const confirmed = confirm(
      `Replace configuration for ${address}?\n\nThis will overwrite the current settings.`
    );
    if (!confirmed) {
      if (statusDiv) statusDiv.style.display = 'none';
      fileInput.value = '';
      if (fileNameSpan) fileNameSpan.textContent = '';
      return;
    }

    // Show importing message
    const messageDiv = document.getElementById('import-message');
    if (messageDiv) {
      messageDiv.textContent = 'Importing...';
      messageDiv.style.backgroundColor = '#e3f2fd';
      messageDiv.style.color = '#1976d2';
    }

    // Import the configuration
    const result = await importDeviceConfiguration(address, file);

    // Show success message
    if (messageDiv) {
      messageDiv.textContent = 'Configuration imported successfully!';
      messageDiv.style.backgroundColor = '#e8f5e9';
      messageDiv.style.color = '#388e3c';
    }

    // Clear file input
    fileInput.value = '';
    if (fileNameSpan) {
      setTimeout(() => {
        if (fileNameSpan) fileNameSpan.textContent = '';
        if (statusDiv) statusDiv.style.display = 'none';
      }, 3000);
    }

    // Refresh device configuration in store
    await deviceStore.getState().actions.refreshDeviceConfig(address, deviceType);

    console.log('Configuration imported successfully');
  } catch (error) {
    console.error('Import failed:', error);
    const messageDiv = document.getElementById('import-message');
    if (messageDiv) {
      messageDiv.textContent = `Import failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
      messageDiv.style.backgroundColor = '#ffebee';
      messageDiv.style.color = '#c62828';
    }

    // Clear file input after error
    const fileInput = document.getElementById('config-file-input') as HTMLInputElement;
    setTimeout(() => {
      fileInput.value = '';
      const fileNameSpan = document.getElementById('file-name');
      if (fileNameSpan) fileNameSpan.textContent = '';
    }, 3000);
  }
}

// Register global handlers
(window as any).handleExportConfig = handleExportConfig;
(window as any).handleImportFile = handleImportFile;
