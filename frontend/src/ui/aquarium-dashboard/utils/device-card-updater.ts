/**
 * Dynamic device card updater
 * 
 * PROBLEM:
 * Previously, any change to a device (connection, status update, settings modification)
 * triggered a full re-render of the entire dashboard by replacing the HTML with
 * dashboardElement.outerHTML = renderProductionDashboard(). This caused:
 * - Flickering and poor UX as the entire page rebuilt
 * - Loss of scroll position
 * - Inefficient DOM operations
 * - Breaking of any active UI interactions
 * 
 * SOLUTION:
 * This module provides intelligent, targeted DOM updates for device cards without
 * full page reloads. It:
 * 1. Subscribes directly to the Zustand deviceStore
 * 2. Compares previous device state to new state (intelligent diffing)
 * 3. Performs targeted DOM operations:
 *    - Add new device cards (with fade-in animation)
 *    - Remove disconnected device cards (with fade-out animation)
 *    - Update existing device cards (preserving scroll position)
 * 4. Updates only the specific cards that changed, leaving the rest untouched
 * 
 * BENEFITS:
 * - Smooth, flicker-free updates
 * - Scroll position preserved
 * - Better performance (only changed elements re-rendered)
 * - Animations for adds/removes provide visual feedback
 * - Active UI interactions (modals, buttons) remain stable
 * 
 * USAGE:
 * Call initializeDeviceCardUpdater() once during app initialization.
 * All device changes are then handled automatically via Zustand subscriptions.
 */

import { deviceStore } from "../../../stores/deviceStore";
import type { DeviceState } from "../../../types/store";
import { renderDeviceSection } from "../devices/device-card";
import type { DeviceStatus } from "../../../types/api";

// Track previous device state to detect changes
let previousDeviceStates = new Map<string, DeviceState>();

/**
 * Initialize the device card updater
 */
export function initializeDeviceCardUpdater(): void {
  // Subscribe to all state changes but intelligently filter to device-only changes
  deviceStore.subscribe((state) => {
    const currentDevices = state.devices;
    
    // Only process if we're on the overview tab
    const isOverviewActive = state.ui.currentView === "overview";
    if (!isOverviewActive) {
      // Just update our tracking state
      previousDeviceStates = new Map(currentDevices);
      return;
    }
    
    // Check if any device actually changed by comparing to previous state
    if (!hasAnyDeviceChanged(currentDevices, previousDeviceStates)) {
      // No device changes, skip DOM update
      return;
    }
    
    // Detect changes and update DOM
    updateDeviceCards(currentDevices);
    
    // Update tracking state
    previousDeviceStates = new Map(currentDevices);
  });
  
  console.log("Device card updater initialized with intelligent filtering");
}

/**
 * Check if any device in the map has actually changed
 */
function hasAnyDeviceChanged(
  current: Map<string, DeviceState>,
  previous: Map<string, DeviceState>
): boolean {
  // Different number of devices = change
  if (current.size !== previous.size) {
    return true;
  }
  
  // Check each device
  for (const [address, currentDevice] of current.entries()) {
    const previousDevice = previous.get(address);
    
    // New device
    if (!previousDevice) {
      return true;
    }
    
    // Device changed
    if (hasDeviceChanged(previousDevice, currentDevice)) {
      return true;
    }
  }
  
  // Check for removed devices
  for (const address of previous.keys()) {
    if (!current.has(address)) {
      return true;
    }
  }
  
  return false;
}

/**
 * Compare device states and perform targeted DOM updates
 */
function updateDeviceCards(currentDevices: Map<string, DeviceState>): void {
  const previousAddresses = new Set(previousDeviceStates.keys());
  const currentAddresses = new Set(currentDevices.keys());
  
  // Filter to only connected devices (overview tab only shows connected)
  const previousConnected = Array.from(previousDeviceStates.values())
    .filter(d => d.status?.connected)
    .map(d => d.address);
  const currentConnected = Array.from(currentDevices.values())
    .filter(d => d.status?.connected)
    .map(d => d.address);
  
  const previousConnectedSet = new Set(previousConnected);
  const currentConnectedSet = new Set(currentConnected);
  
  // Find devices that changed connection state or were added/removed
  const added = currentConnected.filter(addr => !previousConnectedSet.has(addr));
  const removed = previousConnected.filter(addr => !currentConnectedSet.has(addr));
  const updated = currentConnected.filter(addr => {
    if (added.includes(addr)) return false; // Skip newly added
    const prev = previousDeviceStates.get(addr);
    const curr = currentDevices.get(addr);
    return prev && curr && hasDeviceChanged(prev, curr);
  });
  
  // Only log if there are actual changes
  if (added.length > 0 || removed.length > 0 || updated.length > 0) {
    console.log(`🔄 Device card updates: +${added.length} -${removed.length} ~${updated.length}`);
  }
  
  // Handle empty state transitions
  if (previousConnected.length === 0 && currentConnected.length > 0) {
    // Transitioning from empty state to having devices - need full refresh
    console.log('Transitioning from empty state to devices, full refresh needed');
    refreshFullDashboard();
    return;
  } else if (previousConnected.length > 0 && currentConnected.length === 0) {
    // Transitioning from devices to empty state - need full refresh
    console.log('Transitioning to empty state, full refresh needed');
    refreshFullDashboard();
    return;
  }
  
  // Perform DOM updates
  if (removed.length > 0) {
    removed.forEach(address => removeDeviceCard(address));
  }
  
  if (added.length > 0) {
    added.forEach(address => {
      const device = currentDevices.get(address);
      if (device?.status) {
        addDeviceCard(device);
      }
    });
  }
  
  if (updated.length > 0) {
    updated.forEach(address => {
      const device = currentDevices.get(address);
      if (device?.status) {
        updateDeviceCard(device);
      }
    });
  }
  
  // Update device count badge (only if needed)
  if (previousConnected.length !== currentConnected.length) {
    updateDeviceCountBadge(currentConnected.length);
  }
}

/**
 * Check if a device state has meaningfully changed
 */
function hasDeviceChanged(prev: DeviceState, curr: DeviceState): boolean {
  if (!prev.status || !curr.status) return true;
  
  // Check connection state
  if (prev.status.connected !== curr.status.connected) return true;
  
  // Check loading state
  if (prev.isLoading !== curr.isLoading) return true;
  
  // Check error state
  if (prev.error !== curr.error) return true;
  
  // Check if status data changed (stringify for deep comparison)
  const prevStatus = JSON.stringify(prev.status);
  const currStatus = JSON.stringify(curr.status);
  if (prevStatus !== currStatus) return true;
  
  // Check if configuration changed (name, auto_connect, etc)
  const prevConfig = JSON.stringify(prev.configuration);
  const currConfig = JSON.stringify(curr.configuration);
  if (prevConfig !== currConfig) return true;
  
  return false;
}

/**
 * Add a new device card to the DOM
 */
function addDeviceCard(device: DeviceState): void {
  if (!device.status) return;
  
  const container = findDeviceCardContainer();
  if (!container) {
    console.warn("Device card container not found, falling back to full refresh");
    refreshFullDashboard();
    return;
  }
  
  // Create device status object with address
  const deviceWithAddress = {
    ...device.status,
    address: device.address
  };
  
  // Render a temporary container to hold the new card HTML
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = renderDeviceSection("", [deviceWithAddress]);
  
  // Extract the device card from the rendered section
  const newCard = tempDiv.querySelector('.device-card');
  if (newCard) {
    // Add with a fade-in animation
    newCard.classList.add('device-card-entering');
    container.appendChild(newCard);
    
    // Trigger reflow to ensure animation plays
    newCard.getBoundingClientRect();
    
    // Remove animation class after animation completes
    setTimeout(() => {
      newCard.classList.remove('device-card-entering');
    }, 300);
  }
}

/**
 * Remove a device card from the DOM
 */
function removeDeviceCard(address: string): void {
  const card = findDeviceCardElement(address);
  if (card) {
    // Add fade-out animation
    card.classList.add('device-card-leaving');
    
    // Remove after animation completes
    setTimeout(() => {
      card.remove();
    }, 300);
  }
}

/**
 * Update an existing device card in the DOM
 */
function updateDeviceCard(device: DeviceState): void {
  if (!device.status) return;
  
  const existingCard = findDeviceCardElement(device.address);
  if (!existingCard) {
    console.warn(`Device card not found for ${device.address}, adding it`);
    addDeviceCard(device);
    return;
  }
  
  // Create device status object with address
  const deviceWithAddress = {
    ...device.status,
    address: device.address
  };
  
  // Render the updated card
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = renderDeviceSection("", [deviceWithAddress]);
  
  const updatedCard = tempDiv.querySelector('.device-card');
  if (updatedCard) {
    // Quick check: if HTML is identical, skip the update entirely
    if (existingCard.innerHTML === updatedCard.innerHTML) {
      console.log(`Device ${device.address} HTML unchanged, skipping update`);
      return;
    }
    
    // Preserve scroll position
    const scrollTop = window.scrollY;
    
    // Replace the old card with the new one
    existingCard.replaceWith(updatedCard);
    
    // Restore scroll position
    window.scrollTo(0, scrollTop);
    
    console.log(`Updated device card for ${device.address}`);
  }
}

/**
 * Update the device count badge
 */
function updateDeviceCountBadge(count: number): void {
  const badge = document.querySelector('.card-header .badge');
  if (badge) {
    badge.textContent = String(count);
  }
}

/**
 * Find the device card container element
 */
function findDeviceCardContainer(): HTMLElement | null {
  // The container is the grid div within the "Connected Devices" card
  const overviewPanel = document.getElementById('overview-panel');
  if (!overviewPanel) return null;
  
  // Find the grid container (has display: grid style)
  const gridContainer = overviewPanel.querySelector('[style*="display: grid"]') as HTMLElement;
  return gridContainer;
}

/**
 * Find a specific device card element by address
 */
function findDeviceCardElement(address: string): HTMLElement | null {
  // Device cards have onclick handlers with the device address
  const cards = document.querySelectorAll('.device-card');
  
  for (const card of Array.from(cards)) {
    // Check if any button in this card references this address
    const buttons = card.querySelectorAll('button[onclick]');
    for (const button of Array.from(buttons)) {
      const onclick = button.getAttribute('onclick');
      if (onclick?.includes(address)) {
        return card as HTMLElement;
      }
    }
  }
  
  return null;
}

/**
 * Fallback to full dashboard refresh
 */
function refreshFullDashboard(): void {
  import('../render').then(({ refreshDashboard }) => {
    refreshDashboard();
  }).catch(err => {
    console.warn('Could not refresh dashboard:', err);
  });
}
