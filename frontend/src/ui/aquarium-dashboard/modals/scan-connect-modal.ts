/**
 * Scan and Connect Modal - Clean, minimal device discovery interface
 */

import { scanDevices, connectDevice, getDeviceStatus } from "../../../api/devices";
import { useActions } from "../../../stores/deviceStore";
import type { ScanDevice } from "../../../types/api";

export interface ScanState {
  isScanning: boolean;
  devices: ScanDevice[];
  error: string | null;
}

/**
 * Show the scan and connect modal
 */
export async function showScanConnectModal(): Promise<void> {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal-content scan-connect-modal" style="max-width: 500px;">
      <div class="modal-header">
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove();">×</button>
      </div>
      <div class="modal-body">
        ${renderScanInterface()}
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

  // Start scanning immediately
  await performScan(modal);
}

/**
 * Render the scan interface
 */
function renderScanInterface(): string {
  return `
    <div class="scan-interface">
      <div class="scan-status">
        <div class="scan-spinner" style="display: none;"></div>
        <div class="scan-message">Click "Scan" to search for nearby devices</div>
      </div>

      <div class="scan-actions">
        <button class="btn btn-primary scan-button">
          Scan for Devices
        </button>
      </div>

      <div class="devices-list" style="display: none;">
        <h3>Found Devices</h3>
        <div class="devices-container">
          <!-- Devices will be populated here -->
        </div>
      </div>
    </div>
  `;
}

/**
 * Perform device scanning
 */
async function performScan(modal: HTMLElement): Promise<void> {
  const scanButton = modal.querySelector('.scan-button') as HTMLButtonElement;
  const scanSpinner = modal.querySelector('.scan-spinner') as HTMLElement;
  const scanMessage = modal.querySelector('.scan-message') as HTMLElement;
  const devicesList = modal.querySelector('.devices-list') as HTMLElement;
  const devicesContainer = modal.querySelector('.devices-container') as HTMLElement;

  try {
    // Update UI for scanning
    scanButton.disabled = true;
    scanButton.innerHTML = '<span class="scan-spinner"></span> Scanning...';
    scanSpinner.style.display = 'inline-block';
    scanMessage.textContent = 'Scanning for nearby aquarium devices...';

    // Perform scan
    const devices = await scanDevices(5.0);
    
    // Get known devices to show connected state
    const knownStatus = await getDeviceStatus();

    // Update UI with results
    scanButton.disabled = false;
    scanButton.innerHTML = 'Scan Again';
    scanSpinner.style.display = 'none';

    if (devices.length === 0) {
      scanMessage.textContent = 'No aquarium devices found. Try moving closer or check device power.';
      devicesList.style.display = 'none';
    } else {
      const newCount = devices.filter(d => !(d.address in knownStatus)).length;
      if (newCount === 0) {
        scanMessage.textContent = 'All found devices are already added to your dashboard.';
      } else {
        scanMessage.textContent = `Found ${newCount} new device${newCount !== 1 ? 's' : ''} (and ${devices.length - newCount} already added)`;
      }
      
      devicesContainer.innerHTML = devices.map(device => renderDeviceCard(device, device.address in knownStatus)).join('');
      devicesList.style.display = 'block';

      // Initialize event handlers for the newly added connect buttons
      initializeModalHandlers(modal);
    }

  } catch (error) {
    // Handle scan error
    scanButton.disabled = false;
    scanButton.innerHTML = 'Try Again';
    scanSpinner.style.display = 'none';
    scanMessage.textContent = `Scan failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
    devicesList.style.display = 'none';

    console.error('Scan failed:', error);
  }
}

/**
 * Render a device card for the scan results
 */
function renderDeviceCard(device: ScanDevice, isKnown: boolean = false): string {
  return `
    <div class="device-card" data-address="${device.address}" style="${isKnown ? 'opacity: 0.7;' : ''}">
      <div class="device-info">
        <div class="device-name">${device.product}</div>
        <div class="device-address">${device.address}</div>
      </div>
      <div class="device-actions">
        ${isKnown ? 
          `<button class="btn btn-outline" disabled>Connected</button>` : 
          `<button class="btn btn-success btn-sm connect-button" data-address="${device.address}" data-type="${device.device_type}">
             Connect
           </button>`
        }
      </div>
    </div>
  `;
}

/**
 * Handle device connection
 */
async function handleDeviceConnection(address: string, deviceType: string, modal: HTMLElement): Promise<void> {
  const connectButton = modal.querySelector(`[data-address="${address}"] .connect-button`) as HTMLButtonElement;
  const originalText = connectButton.textContent;

  try {
    // Update button to show connecting state
    connectButton.disabled = true;
    connectButton.innerHTML = '<span class="scan-spinner"></span> Connecting...';

    // Attempt connection
    await connectDevice(address, deviceType);

    // Success - update button and show notification
    connectButton.className = 'btn btn-success btn-sm';
    connectButton.innerHTML = '✓ Connected';

    // Show success notification
    useActions().addNotification({
      type: 'success',
      message: `Successfully connected to ${address}`
    });

    // Refresh dashboard data
    const { refreshDeviceStatusOnly } = await import('../services/data-service');
    await refreshDeviceStatusOnly();

    // Device card updater will automatically show the new device
    // No need for full refreshDashboard() call

    // Close modal after a brief delay
    setTimeout(() => {
      modal.remove();
    }, 1500);

  } catch (error) {
    // Connection failed - reset button
    connectButton.disabled = false;
    connectButton.textContent = originalText;
    connectButton.className = 'btn btn-danger btn-sm';

    // Show error notification
    useActions().addNotification({
      type: 'error',
      message: `Failed to connect to ${address}: ${error instanceof Error ? error.message : 'Unknown error'}`
    });

    console.error('Connection failed:', error);
  }
}

/**
 * Initialize modal event handlers
 */
function initializeModalHandlers(modal: HTMLElement): void {
  // Scan button handler
  const scanButton = modal.querySelector('.scan-button');
  if (scanButton) {
    scanButton.addEventListener('click', () => performScan(modal));
  }

  // Connect button handlers (delegated)
  const devicesContainer = modal.querySelector('.devices-container');
  if (devicesContainer) {
    devicesContainer.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const connectButton = target.closest('.connect-button') as HTMLButtonElement;
      if (connectButton) {
        const address = connectButton.dataset.address;
        const deviceType = connectButton.dataset.type;
        if (address && deviceType) {
          handleDeviceConnection(address, deviceType, modal);
        }
      }
    });
  }
}

// Initialize handlers when modal is shown
export function initializeScanConnectHandlers(): void {
  // This will be called when the modal is created
  // Handlers are set up in the showScanConnectModal function
}
