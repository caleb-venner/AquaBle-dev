/**
 * Dashboard data service - handles all API calls and data loading
 */

import { getDeviceStatus } from "../../../api/devices";
import { deviceStore } from "../../../stores/deviceStore";

/**
 * Load all dashboard data from APIs
 */
export async function loadAllDashboardData(): Promise<void> {
  const actions = deviceStore.getState().actions;
  actions.setGlobalError(null);

  try {
    // Initialize the Zustand store with two-stage loading
    console.log("🔄 Initializing Zustand store...");
    await actions.initializeStore();
    console.log("✅ Zustand store initialized");

    // Fetch device status
    console.log("🌐 Fetching device status from API");
    try {
      const newStatus = await getDeviceStatus();
      
      // Update device status in Zustand store
      const configPromises: Promise<any>[] = [];
      
      for (const [address, status] of Object.entries(newStatus)) {
        actions.updateDevice(address, status);
        
        // Fetch configuration for each device
        console.log(`📥 Fetching configuration for ${address}...`);
        const configPromise = actions.refreshDeviceConfig(address, status.device_type as 'doser' | 'light')
          .catch((err: any) => console.error(`Failed to load config for ${address}:`, err));
        configPromises.push(configPromise);
      }
      
      // Wait for all configurations to load
      await Promise.allSettled(configPromises);
      
      console.log("✅ Device status loaded:", Object.keys(newStatus).length, "devices");
    } catch (statusErr) {
      console.error("❌ Failed to load device status:", statusErr);
      actions.setGlobalError("Failed to load device status");
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : String(err);
    console.error("❌ Failed to load dashboard data:", errorMessage);
    actions.setGlobalError(`Failed to load dashboard data: ${errorMessage}`);
  }
}

/**
 * Refresh only device status after connection/disconnection
 */
export async function refreshDeviceStatusOnly(): Promise<void> {
  try {
    // Refresh Zustand store
    const actions = deviceStore.getState().actions;
    await actions.refreshDevices();
  } catch (error) {
    console.error("❌ Failed to refresh device status:", error);
  }
}

// ============================================================================
// Debounce and caching utilities for configuration fetches
// ============================================================================

let configFetchTimeout: number | null = null;
let lastConfigFetchTime = 0;
const CONFIG_FETCH_DEBOUNCE_MS = 2000; // Wait 2 seconds before refetching configs

/**
 * Debounced configuration fetch (prevents rapid repeated fetches)
 * Useful after commands complete to avoid multiple config refreshes
 */
export async function debouncedRefreshConfigurations(): Promise<void> {
  const now = Date.now();
  const timeSinceLastFetch = now - lastConfigFetchTime;

  // If we just fetched recently, debounce the request
  if (timeSinceLastFetch < CONFIG_FETCH_DEBOUNCE_MS) {
    console.log(`⏱️  Config fetch debounced (last fetch: ${timeSinceLastFetch}ms ago)`);

    // Clear any pending timeout
    if (configFetchTimeout !== null) {
      clearTimeout(configFetchTimeout);
    }

    // Schedule a deferred fetch
    const remainingWait = CONFIG_FETCH_DEBOUNCE_MS - timeSinceLastFetch;
    configFetchTimeout = window.setTimeout(() => {
      console.log("🔄 Running deferred configuration fetch");
      debouncedRefreshConfigurations().catch((err: any) =>
        console.error("Failed to refresh configs:", err)
      );
    }, remainingWait);
    return;
  }

  // Enough time has passed, fetch now
  console.log("🔄 Fetching configurations (not debounced)");
  lastConfigFetchTime = now;

  try {
    const { useActions } = await import("../../../stores/deviceStore");
    await useActions().loadConfigurations();
  } catch (error) {
    console.error("Failed to load configurations:", error);
  }
}
