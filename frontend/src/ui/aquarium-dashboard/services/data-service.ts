/**
 * Dashboard data service - handles all API calls and data loading
 */

import {
  getConfigurationSummary,
  listDoserMetadata,
  listLightMetadata,
  type ConfigurationSummary,
} from "../../../api/configurations";
import { getDeviceStatus } from "../../../api/devices";
import type { StatusResponse } from "../../../types/models";
import type { DeviceMetadata, LightMetadata } from "../../../api/configurations";
import {
  setDoserMetadata,
  setLightMetadata,
  setSummary,
  setDeviceStatus,
  setError,
  markDeviceStable,
  markDeviceUnstable,
  getDashboardState,
} from "../state";

/**
 * Load all dashboard data from APIs
 */
export async function loadAllDashboardData(): Promise<void> {
  setError(null);

  try {
    // Initialize the Zustand store with two-stage loading
    console.log("🔄 Initializing Zustand store...");
    const { useActions } = await import("../../../stores/deviceStore");
    await useActions().initializeStore();
    console.log("✅ Zustand store initialized");

    // Continue with dashboard-specific data loading
    // Load metadata, summary, and device status in parallel
    // (configurations and status already loaded by initializeStore)
    const results = await Promise.allSettled([
      getConfigurationSummary(),
      getDeviceStatus(),
      listDoserMetadata(),
      listLightMetadata(),
    ]);

    // Handle summary (gracefully fail if it errors)
    if (results[0].status === "fulfilled") {
      setSummary(results[0].value);
    } else {
      console.error("❌ Failed to load summary:", results[0].reason);
      // Create a fallback summary (configurations already loaded in Zustand)
      const fallbackSummary: ConfigurationSummary = {
        total_configurations: 0,
        dosers: {
          count: 0,
          addresses: [],
        },
        lights: {
          count: 0,
          addresses: [],
        },
        storage_paths: {
          doser_configs: "~/.aquable/devices",
          light_profiles: "~/.aquable/devices",
        },
      };
      setSummary(fallbackSummary);
    }

    // Handle device status
    if (results[1].status === "fulfilled") {
      const newStatus = results[1].value;
      const previousState = getDashboardState();
      const previousStatus = previousState.deviceStatus;

      setDeviceStatus(newStatus);

      // Track connection stability changes
      Object.entries(newStatus).forEach(([address, status]) => {
        const previousDeviceStatus = previousStatus?.[address];

        // If device just disconnected
        if (previousDeviceStatus?.connected && !status.connected) {
          markDeviceUnstable(address);
        }
        // If device is connected and was previously tracked as unstable, reset if it's been stable for a while
        else if (status.connected && previousDeviceStatus?.connected) {
          // Device has been consistently connected, mark as stable
          markDeviceStable(address);
        }
      });
    } else {
      console.error("❌ Failed to load device status:", results[1].reason);
      setDeviceStatus({});
    }

    // Handle doser metadata
    if (results[2].status === "fulfilled") {
      setDoserMetadata(results[2].value);
    } else {
      console.error("❌ Failed to load doser metadata:", results[2].reason);
      setDoserMetadata([]);
    }

    // Handle light metadata
    if (results[3].status === "fulfilled") {
      setLightMetadata(results[3].value);
    } else {
      console.error("❌ Failed to load light metadata:", results[3].reason);
      setLightMetadata([]);
    }

    const state = {
      devices: results[1].status === "fulfilled" ? Object.keys(results[1].value).length : 0,
      doserMetadata: results[2].status === "fulfilled" ? results[2].value.length : 0,
      lightMetadata: results[3].status === "fulfilled" ? results[3].value.length : 0,
      summary: results[0].status === "fulfilled" ? "loaded" : "fallback"
    };

    console.log("✅ Loaded dashboard data:", state);
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : String(err);
    console.error("❌ Failed to load dashboard data:", errorMessage);
    setError(`Failed to load dashboard data: ${errorMessage}`);
    // Ensure deviceStatus is set to empty object so UI shows "no devices" instead of "no data"
    setDeviceStatus({});
  }
}

/**
 * Refresh only device status after connection/disconnection
 */
export async function refreshDeviceStatusOnly(): Promise<void> {
  try {
    // Refresh Zustand store
    const { useActions } = await import("../../../stores/deviceStore");
    await useActions().refreshDevices();

    // Also refresh local dashboard state for compatibility
    const status = await getDeviceStatus();
    setDeviceStatus(status);
  } catch (error) {
    console.error("❌ Failed to refresh device status:", error);
  }
}
