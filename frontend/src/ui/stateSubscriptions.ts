// State subscription system for automatic UI updates
// 
// SIMPLIFIED: This file now provides a thin wrapper around Zustand's built-in
// subscription system. The complex bridging logic has been removed since all
// state is now managed by deviceStore.
//
// Uses targeted DOM updates for device cards instead of full page refreshes.

import { deviceStore } from "../stores/deviceStore";
import { renderNotifications } from "./notifications";
import { initializeDeviceCardUpdater } from "./aquarium-dashboard/utils/device-card-updater";

let unsubscribeCallbacks: (() => void)[] = [];

export function setupStateSubscriptions(): void {
  console.log('Setting up state subscriptions with targeted device card updates');
  
  // Initialize the dynamic device card updater
  // This handles all device card additions/removals/updates without full page refresh
  initializeDeviceCardUpdater();
  
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

  // Subscribe to view changes - these require full dashboard refresh
  let previousView = deviceStore.getState().ui.currentView;
  const unsubscribeView = deviceStore.subscribe(
    (state) => {
      if (state.ui.currentView !== previousView) {
        previousView = state.ui.currentView;
        console.log(`📱 View changed to: ${previousView}`);
        refreshDashboard();
      }
    }
  );

  // Store cleanup function
  unsubscribeCallbacks = [unsubscribeNotifications, unsubscribeView];
  
  console.log('State subscriptions active with targeted updates');
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
