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
import {
  cacheService,
  CACHE_KEYS,
  CACHE_TTL,
  invalidateMetadataCache,
} from "./cache-service";

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

    // Prepare API calls with caching
    // Metadata uses cache; status is always fresh; summary is derived from configs
    const apiCalls = await Promise.allSettled([
      // Summary: derive from already-loaded configurations (no API call needed)
      (async () => {
        console.log("📦 Deriving summary from loaded configurations");
        const { useConfigurations } = await import("../../../stores/deviceStore");
        const configurations = useConfigurations();
        
        // Derive summary from loaded configurations
        const doserConfigs = Array.from(configurations.dosers?.values?.() || []) as any[];
        const lightConfigs = Array.from(configurations.lights?.values?.() || []) as any[];
        
        const summary: ConfigurationSummary = {
          total_configurations: doserConfigs.length + lightConfigs.length,
          dosers: {
            count: doserConfigs.length,
            addresses: doserConfigs.map((d: any) => d.id || ''),
          },
          lights: {
            count: lightConfigs.length,
            addresses: lightConfigs.map((l: any) => l.id || ''),
          },
          storage_paths: {
            doser_configs: "~/.aquable/devices",
            light_profiles: "~/.aquable/devices",
          },
        };

        // Cache the derived summary
        cacheService.set(CACHE_KEYS.CONFIGURATION_SUMMARY, summary, CACHE_TTL.SUMMARY);
        return summary;
      })(),
      
      // Status: always fresh (no caching)
      (async () => {
        console.log("🌐 Fetching device status from API");
        return await getDeviceStatus();
      })(),
      
      // Doser Metadata: use cache if available
      (async () => {
        const cached = cacheService.get<DeviceMetadata[]>(CACHE_KEYS.DOSER_METADATA);
        if (cached) {
          console.log("📦 Using cached doser metadata");
          return cached;
        }
        console.log("🌐 Fetching doser metadata from API");
        const result = await listDoserMetadata();
        cacheService.set(CACHE_KEYS.DOSER_METADATA, result, CACHE_TTL.METADATA);
        return result;
      })(),
      
      // Light Metadata: use cache if available
      (async () => {
        const cached = cacheService.get<LightMetadata[]>(CACHE_KEYS.LIGHT_METADATA);
        if (cached) {
          console.log("📦 Using cached light metadata");
          return cached;
        }
        console.log("🌐 Fetching light metadata from API");
        const result = await listLightMetadata();
        cacheService.set(CACHE_KEYS.LIGHT_METADATA, result, CACHE_TTL.METADATA);
        return result;
      })(),
    ]);

    // Handle summary (gracefully fail if it errors)
    if (apiCalls[0].status === "fulfilled") {
      setSummary(apiCalls[0].value);
    } else {
      console.error("❌ Failed to load summary:", apiCalls[0].reason);
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
    if (apiCalls[1].status === "fulfilled") {
      const newStatus = apiCalls[1].value;
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
      console.error("❌ Failed to load device status:", apiCalls[1].reason);
      setDeviceStatus({});
    }

    // Handle doser metadata
    if (apiCalls[2].status === "fulfilled") {
      setDoserMetadata(apiCalls[2].value);
    } else {
      console.error("❌ Failed to load doser metadata:", apiCalls[2].reason);
      setDoserMetadata([]);
    }

    // Handle light metadata
    if (apiCalls[3].status === "fulfilled") {
      setLightMetadata(apiCalls[3].value);
    } else {
      console.error("❌ Failed to load light metadata:", apiCalls[3].reason);
      setLightMetadata([]);
    }

    const state = {
      devices: apiCalls[1].status === "fulfilled" ? Object.keys(apiCalls[1].value).length : 0,
      doserMetadata: apiCalls[2].status === "fulfilled" ? apiCalls[2].value.length : 0,
      lightMetadata: apiCalls[3].status === "fulfilled" ? apiCalls[3].value.length : 0,
      summary: apiCalls[0].status === "fulfilled" ? "loaded" : "fallback"
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
      debouncedRefreshConfigurations().catch(err =>
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
