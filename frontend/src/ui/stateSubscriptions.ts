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
  
  // Track connected device count to trigger refreshes only when it changes
  // This prevents full dashboard refreshes when devices are loading but not connected yet
  let previousConnectedCount = 0;
  
  const unsubscribeDevices = deviceStore.subscribe(
    (state) => {
      const currentConnectedCount = Array.from(state.devices.values()).filter(
        device => device.status?.connected
      ).length;
      
      // Only refresh if the connected count actually changed
      if (currentConnectedCount !== previousConnectedCount) {
        console.log(`📱 Connected devices changed to: ${currentConnectedCount}`);
        previousConnectedCount = currentConnectedCount;
        refreshDashboard();
      }
    }
  );

  // Subscribe to notification changes only
  let previousNotificationCount = 0;
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
