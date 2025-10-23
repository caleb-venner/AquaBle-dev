// State subscription system for automatic UI updates
// 
// SIMPLIFIED: This file now provides a thin wrapper around Zustand's built-in
// subscription system. The complex bridging logic has been removed since all
// state is now managed by deviceStore.
//
// TODO: Migrate components to use deviceStore.subscribe() directly and remove this file.

import { deviceStore } from "../stores/deviceStore";
import { renderNotifications } from "./notifications";

let unsubscribeCallbacks: (() => void)[] = [];

export function setupStateSubscriptions(): void {
  console.log('Setting up state subscriptions (delegating to Zustand)');
  
  let previousDeviceCount = 0;
  let previousNotificationCount = 0;
  let previousDeviceStates: Map<string, boolean> = new Map(); // Track connection state per device

  // Subscribe to device changes to refresh dashboard
  const unsubscribeDevices = deviceStore.subscribe(
    (state) => {
      const currentDeviceCount = state.devices.size;
      
      // Check if device count changed
      const deviceCountChanged = currentDeviceCount !== previousDeviceCount;
      
      // Check if any device's connection status changed
      let deviceStatusChanged = false;
      state.devices.forEach((device, address) => {
        const currentConnected = device.status?.connected || false;
        const previousConnected = previousDeviceStates.get(address);
        
        if (previousConnected !== currentConnected) {
          deviceStatusChanged = true;
          previousDeviceStates.set(address, currentConnected);
          console.log(`📱 Device ${address} connection changed to: ${currentConnected}`);
        }
      });
      
      // Also check for removed devices
      previousDeviceStates.forEach((_, address) => {
        if (!state.devices.has(address)) {
          deviceStatusChanged = true;
          previousDeviceStates.delete(address);
        }
      });
      
      if (deviceCountChanged) {
        console.log(`📱 Device count changed: ${currentDeviceCount} devices`);
        previousDeviceCount = currentDeviceCount;
        refreshDashboard();
      }
    }
  );

  // Subscribe to notification changes only
  const unsubscribeNotifications = deviceStore.subscribe(
    (state) => {
      const notificationCount = state.ui.notifications.length;
      if (notificationCount !== previousNotificationCount) {
        previousNotificationCount = notificationCount;
        renderNotifications();
      }
    }
  );

  // Store cleanup function
  unsubscribeCallbacks = [unsubscribeDevices, unsubscribeNotifications];
  
  console.log('State subscriptions active');
}

/**
 * Refresh the dashboard by importing and calling the render function
 */
function refreshDashboard(): void {
  import('./aquarium-dashboard/render').then(({ refreshDashboard }) => {
    refreshDashboard();
  }).catch(err => {
    console.warn('Could not refresh dashboard:', err);
  });
}

export function cleanupStateSubscriptions(): void {
  console.log('Cleaning up state subscriptions');
  unsubscribeCallbacks.forEach(cleanup => cleanup());
  unsubscribeCallbacks = [];
}

// Legacy function - no longer needed with Zustand
export function throttledDashboardUpdate(): void {
  console.warn('throttledDashboardUpdate is deprecated. Zustand handles updates automatically.');
}
