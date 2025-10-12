// State subscription system for automatic UI updates

import { deviceStore } from "../stores/deviceStore";
import { renderNotifications } from "./notifications";

let unsubscribeCallbacks: (() => void)[] = [];

export function setupStateSubscriptions(): void {
  let previousDevicesSize = deviceStore.getState().devices.size;
  let previousUI = deviceStore.getState().ui;
  let previousQueueLength = deviceStore.getState().commandQueue.length;
  let previousDeviceData = new Map();

  // Subscribe to device changes
  const unsubscribeDevices = deviceStore.subscribe(
    (state) => {
      const devices = state.devices;
      let hasChanged = false;

      // Check if device count changed
      if (devices.size !== previousDevicesSize) {
        console.log(`Device count changed: ${devices.size} devices`);
        previousDevicesSize = devices.size;
        hasChanged = true;
      }

      // Check if any device status changed (connection, last updated, etc.)
      devices.forEach((device, address) => {
        const previous = previousDeviceData.get(address);
        if (!previous ||
            previous.lastUpdated !== device.lastUpdated ||
            previous.status?.connected !== device.status?.connected ||
            previous.isLoading !== device.isLoading ||
            previous.error !== device.error) {
          console.log(`Device ${address} status changed`);
          hasChanged = true;
        }
      });

      // Update our cache
      previousDeviceData = new Map(devices);

      if (hasChanged) {
        updateDashboardView();
      }
    }
  );

  // Subscribe to UI state changes
  const unsubscribeUI = deviceStore.subscribe(
    (state) => {
      const ui = state.ui;
      // Update dashboard for loading/scanning state changes
      if (ui.globalError !== previousUI.globalError) {
        updateDashboardView();
      }

      // Update notifications when they change
      if (ui.notifications.length !== previousUI.notifications.length) {
        renderNotifications();
      }

      previousUI = ui;
    }
  );

  // Subscribe to command queue changes
  const unsubscribeQueue = deviceStore.subscribe(
    (state) => {
      const queue = state.commandQueue;
      if (queue.length !== previousQueueLength) {
        console.log(`Command queue changed: ${queue.length} commands`);
        previousQueueLength = queue.length;
        // Update any UI elements that show command queue status
        updateCommandQueueIndicator(queue.length);
      }
    }
  );

  // Store cleanup functions
  unsubscribeCallbacks = [unsubscribeDevices, unsubscribeUI, unsubscribeQueue];
}

export function cleanupStateSubscriptions(): void {
  unsubscribeCallbacks.forEach(cleanup => cleanup());
  unsubscribeCallbacks = [];
}

function updateCommandQueueIndicator(queueLength: number): void {
  // Update any command queue indicators in the UI
  const indicators = document.querySelectorAll('.command-queue-indicator');
  indicators.forEach(indicator => {
    if (queueLength > 0) {
      indicator.textContent = `${queueLength}`;
      indicator.classList.add('active');
    } else {
      indicator.textContent = '';
      indicator.classList.remove('active');
    }
  });
}

// Update dashboard view safely without circular imports
function updateDashboardView(): void {
  // Look for the dashboard container and trigger a re-render
  const modernContainer = document.getElementById("modern-dashboard-content");
  if (modernContainer) {
    // Trigger a custom event that the modern dashboard can listen to
    document.dispatchEvent(new CustomEvent('dashboard-update-requested'));
  }

  // Also try to call any global update function if available
  if (typeof (window as any).updateModernDashboard === 'function') {
    (window as any).updateModernDashboard();
  }

  // Update the production dashboard if it exists
  const productionDashboard = document.querySelector('.production-dashboard');
  if (productionDashboard) {
    // Update the dashboard state with current Zustand store data
    updateDashboardStateFromZustand();

    // Trigger dashboard refresh
    if (typeof (window as any).refreshDashboard === 'function') {
      (window as any).refreshDashboard();
    } else {
      // Import and call refreshDashboard directly
      import('./aquarium-dashboard/render').then(({ refreshDashboard }) => {
        refreshDashboard();
      }).catch(err => {
        console.warn('Could not refresh dashboard:', err);
      });
    }
  }
}

// Bridge function to sync Zustand store data to dashboard state
function updateDashboardStateFromZustand(): void {
  const zustandState = deviceStore.getState();

  // Convert Zustand device data to dashboard state format
  const deviceStatusObj: { [address: string]: any } = {};
  zustandState.devices.forEach((device, address) => {
    if (device.status) {
      deviceStatusObj[address] = device.status;
    }
  });

  // Update dashboard state
  import('./aquarium-dashboard/state').then(({ setDeviceStatus }) => {
    setDeviceStatus(deviceStatusObj);
  }).catch(err => {
    console.warn('Could not update dashboard state:', err);
  });
}

// Throttled update functions to prevent excessive re-renders
let updateTimeout: number | null = null;

export function throttledDashboardUpdate(): void {
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }

  updateTimeout = window.setTimeout(() => {
    updateDashboardView();
    updateTimeout = null;
  }, 100); // Throttle to max 10 updates per second
}
