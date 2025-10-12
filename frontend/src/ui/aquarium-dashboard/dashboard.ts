/**
 * Main dashboard module - entry point for the refactored dashboard
 */

import { renderProductionDashboard, refreshDashboard } from "./render";
import { loadAllDashboardData } from "./services/data-service";
import { setCurrentTab, getDashboardState } from "./state";
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
    setCurrentTab(tab);
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

  // Data refresh
  (window as any).handleRefreshAll = async () => {
    const { useActions } = await import("../../stores/deviceStore");
    const { refreshDeviceStatusOnly } = await import('./services/data-service');
    const { getDashboardState, setRefreshing } = await import('./state');
    const { refreshDashboard } = await import('./render');

    try {
      setRefreshing(true);
      refreshDashboard(); // Show refreshing state

      // Only refresh device status, not all data
      await refreshDeviceStatusOnly();

      useActions().addNotification({
        type: 'success',
        message: 'Device status refreshed successfully'
      });
    } catch (error) {
      useActions().addNotification({
        type: 'error',
        message: `Failed to refresh device status: ${error instanceof Error ? error.message : String(error)}`
      });
    } finally {
      setRefreshing(false);
      refreshDashboard(); // Remove refreshing state
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
    if (deviceType === 'doser') {
      const { showDoserDeviceSettingsModal } = await import('./modals/device-modals');
      const state = getDashboardState();
      const device = state.deviceStatus?.[address];
      if (device) {
        // Convert to DoserDevice format for the modal
        const doserDevice = {
          id: address,
          name: device.model_name || undefined,
          heads: [] // Will be populated by the modal
        };
        showDoserDeviceSettingsModal(doserDevice);
      }
    } else if (deviceType === 'light') {
      const { showLightDeviceSettingsModal } = await import('./modals/device-modals');
      const state = getDashboardState();
      const device = state.deviceStatus?.[address];
      if (device) {
        // Convert to LightDevice format for the modal
        const lightDevice = {
          id: address,
          name: device.model_name || undefined,
          channels: [], // Will be populated by the modal
          profile: { mode: 'manual' as const, levels: {} }
        };
        showLightDeviceSettingsModal(lightDevice);
      }
    }
  };

  (window as any).toggleDeviceConnection = async (address: string) => {
    const { connectDevice, disconnectDevice } = await import("../../api/devices");
    const { useActions } = await import("../../stores/deviceStore");
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
      const state = getDashboardState();
      const device = state.deviceStatus?.[address];
      const isCurrentlyConnected = device?.connected;

      if (isCurrentlyConnected) {
        // Disconnect if currently connected
        await disconnectDevice(address);
        await refreshDeviceStatusOnly();

        // Refresh dashboard UI to reflect disconnection status
        const { refreshDashboard } = await import('./render');
        refreshDashboard();

        useActions().addNotification({
          type: 'success',
          message: `Successfully disconnected from device`
        });

        // Update button text to reflect new state
        if (connectButton) {
          connectButton.disabled = false;
          connectButton.classList.remove('connecting');
          connectButton.innerHTML = 'Connect';
        }
      } else {
        // Connect if currently disconnected
        await connectDevice(address);
        await refreshDeviceStatusOnly();

        // Refresh dashboard UI to reflect connection status
        const { refreshDashboard } = await import('./render');
        refreshDashboard();

        useActions().addNotification({
          type: 'success',
          message: `Successfully connected to device`
        });

        // Update button text to reflect new state
        if (connectButton) {
          connectButton.disabled = false;
          connectButton.innerHTML = 'Disconnect';
        }
      }
    } catch (error) {
      useActions().addNotification({
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
loadAllDashboardData();
