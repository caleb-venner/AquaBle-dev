/**
 * Main dashboard module - entry point for the refactored dashboard
 */

import { renderProductionDashboard, refreshDashboard } from "./render";
import { loadAllDashboardData } from "./services/data-service";
import { initializePolling, cleanupPolling } from "./services/polling-service";
import { deviceStore } from "../../stores/deviceStore";
import { renderWattageCalculator, calculateWattageFromInputs, setWattageTestCase } from "./components/wattage-calculator";
import "./modals/device-config-modal"; // Import the new unified device config modal
import "./modals/scan-connect-modal"; // Import the scan and connect modal

// Export the main render function
export { renderProductionDashboard, refreshDashboard };

// Export data loading
export { loadAllDashboardData };

// Export wattage calculator functions for global handlers
export { calculateWattageFromInputs, setWattageTestCase };

// Initialize global handlers
export function initializeDashboardHandlers(): void {
  // Tab switching
  (window as any).switchTab = async (tab: "overview" | "dev") => {
    deviceStore.getState().actions.setCurrentView(tab);
    refreshDashboard();
  };

  // Device scanning
  (window as any).handleScanDevices = async () => {
    const { showScanConnectModal } = await import('./modals/scan-connect-modal');
    await showScanConnectModal();
  };

  // Make refreshDashboard globally available
  (window as any).refreshDashboard = () => {
    import('./render').then(({ refreshDashboard }) => {
      refreshDashboard();
    });
  };

  // Theme toggle
  (window as any).toggleTheme = () => {
    const currentTheme = localStorage.getItem('theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    console.log('Toggling theme from', currentTheme, 'to', newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.className = newTheme === 'dark' ? 'dark-theme' : '';
    console.log('Updated document.documentElement.className to:', document.documentElement.className);
    (window as any).refreshDashboard();
  };

  // Device raw data toggle
  (window as any).toggleDeviceRawData = (deviceId: string) => {
    const content = document.getElementById(`${deviceId}-content`);
    const icon = document.getElementById(`${deviceId}-icon`);

    if (content && icon) {
      const isExpanded = content.style.display !== 'none';
      content.style.display = isExpanded ? 'none' : 'block';
      icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(90deg)';
    }
  };

  // Data refresh
  (window as any).handleRefreshAll = async () => {
    const { refreshDeviceStatusOnly } = await import('./services/data-service');

    // Find the refresh button and update its state
    const refreshButton = document.querySelector('[onclick*="handleRefreshAll"]') as HTMLButtonElement;
    const originalContent = refreshButton?.innerHTML;

    try {
      // Update button to show loading state
      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<span class="scan-spinner"></span> Refreshing...';
      }

      // Only refresh device status, not all data
      // The device card updater will automatically update cards when store changes
      await refreshDeviceStatusOnly();

      deviceStore.getState().actions.addNotification({
        type: 'success',
        message: 'Device status refreshed successfully'
      });
    } catch (error) {
      deviceStore.getState().actions.addNotification({
        type: 'error',
        message: `Failed to refresh device status: ${error instanceof Error ? error.message : String(error)}`
      });
    } finally {
      // Restore button state
      if (refreshButton && originalContent) {
        refreshButton.disabled = false;
        refreshButton.innerHTML = originalContent;
      }
    }
  };

  (window as any).handleRefreshDevice = async (address: string) => {
    const { refreshDeviceStatus } = await import("../../api/devices");
    const { refreshDeviceStatusOnly } = await import('./services/data-service');

    const refreshButton = document.querySelector(`[onclick*="handleRefreshDevice('${address}')"]`) as HTMLButtonElement;
    const originalContent = refreshButton?.innerHTML;

    try {
      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<span class="scan-spinner"></span>';
      }

      await refreshDeviceStatus(address);
      await refreshDeviceStatusOnly(); // Refresh all statuses to keep UI consistent

      deviceStore.getState().actions.addNotification({
        type: 'success',
        message: `Device ${address} status refreshed`,
        autoHide: true,
      });
    } catch (error) {
      deviceStore.getState().actions.addNotification({
        type: 'error',
        message: `Failed to refresh device status: ${error instanceof Error ? error.message : String(error)}`
      });
    } finally {
      if (refreshButton && originalContent) {
        refreshButton.disabled = false;
        refreshButton.innerHTML = originalContent;
      }
    }
  };

  // Initialize wattage calculator when dev tab is loaded
  setTimeout(() => {
    if (document.getElementById('watt-red')) {
      calculateWattageFromInputs();
    }
  }, 100);

  // Device management handlers (placeholder for future use)
  (window as any).handleDeleteDevice = async (address: string, deviceType: string) => {
    console.log('Delete device:', address, deviceType);
    // TODO: Implement device deletion via API
  };

  // Device configuration (nickname, auto-connect, head names)
  (window as any).handleDeviceSettings = async (address: string, deviceType: string) => {
    const { showDeviceConfigModal } = await import('./modals/device-config-modal');
    showDeviceConfigModal(address, deviceType as 'doser' | 'light');
  };

  // Legacy device settings (for command interface)
  (window as any).openDeviceSettings = async (address: string, deviceType: string) => {
    const { showDoserDeviceSettingsModal, showLightDeviceSettingsModal } = await import('./modals/device-modals');
    
    try {
      // Refresh device configuration from API and update store
      const device = await deviceStore.getState().actions.refreshDeviceConfig(
        address, 
        deviceType as 'doser' | 'light'
      );
      
      // Show modal with fresh data from store
      if (deviceType === 'doser') {
        showDoserDeviceSettingsModal(device as any);
      } else if (deviceType === 'light') {
        showLightDeviceSettingsModal(device as any);
      }
    } catch (error) {
      console.error(`Failed to load ${deviceType} configuration:`, error);
      deviceStore.getState().actions.addNotification({
        type: 'error',
        message: `Failed to load ${deviceType} settings`,
        autoHide: true,
      });
    }
  };

  (window as any).toggleDeviceConnection = async (address: string) => {
    const { connectDevice, disconnectDevice } = await import("../../api/devices");
    const { refreshDeviceStatusOnly } = await import('./services/data-service');

    // Find and update the connect button
    const connectButton = document.querySelector(`[onclick*="toggleDeviceConnection('${address}')"]`) as HTMLButtonElement;
    if (connectButton) {
      const originalText = connectButton.textContent?.trim();
      connectButton.disabled = true;
      connectButton.classList.add('connecting');
      connectButton.textContent = 'Connecting...';
    }

    try {
      // Check current connection state to determine action
      const zustandState = deviceStore.getState();
      const device = zustandState.devices.get(address)?.status;
      const isCurrentlyConnected = device?.connected;

      if (isCurrentlyConnected) {
        // Disconnect if currently connected
        await disconnectDevice(address);
        await refreshDeviceStatusOnly();

        // Device card updater will automatically update the card when store changes
        // No need for refreshDashboard() - targeted update happens automatically

        deviceStore.getState().actions.addNotification({
          type: 'success',
          message: `Successfully disconnected from device`
        });

        // Update button text to reflect new state (immediate feedback)
        if (connectButton) {
          connectButton.disabled = false;
          connectButton.classList.remove('connecting');
          connectButton.innerHTML = 'Connect';
        }
      } else {
        // Connect if currently disconnected
        const connectedStatus = await connectDevice(address);
        
        // Immediately update the Zustand store with the connected status
        deviceStore.getState().actions.updateDevice(address, connectedStatus);
        
        // Also refresh all device statuses to get updated "connected" states for other devices
        await refreshDeviceStatusOnly();

        // Device card updater will automatically update the card when store changes
        // No need for refreshDashboard() - targeted update happens automatically

        deviceStore.getState().actions.addNotification({
          type: 'success',
          message: `Successfully connected to device`
        });

        // Update button text to reflect new state (immediate feedback)
        if (connectButton) {
          connectButton.disabled = false;
          connectButton.innerHTML = 'Disconnect';
        }
      }
    } catch (error) {
      deviceStore.getState().actions.addNotification({
        type: 'error',
        message: `Failed to ${connectButton?.textContent?.includes('Disconnect') ? 'disconnect' : 'connect'} to device: ${error instanceof Error ? error.message : 'Unknown error'}`
      });

      // Restore button to original state
      if (connectButton) {
        connectButton.disabled = false;
        connectButton.classList.remove('connecting');
        connectButton.innerHTML = connectButton.textContent?.includes('Disconnect') ? 'Disconnect' : 'Connect';
      }
    }
  };

  /*
   * ====================================================================
   * DEVICE COMMAND HANDLERS REMOVED - Phase 2 Cleanup
   * ====================================================================
   * The following handlers have been removed as part of dashboard overhaul:
   * - handleClearAutoSettings
   * - switchLightSettingsTab
   * - handleTurnLightOn/Off
   * - handleSetManualMode
   * - handleEnableAutoMode
   * - handleManualBrightness
   * - handleAddAutoProgram
   * - handleDeleteAutoProgram
   * - handleDeleteSpecificAutoProgram
   * - handleEditAutoProgram
   * - selectLightMode
   * - selectHead
   * - getLightConfiguration
   * - deleteAutoSetting
   * - testLightModal
   *
   * These handlers provided individual device control functionality that
   * will be replaced with a new robust command system in Phase 3.
   * ====================================================================
   */
}

// Auto-load data on module import
// loadAllDashboardData(); // Moved to productionMain.ts
