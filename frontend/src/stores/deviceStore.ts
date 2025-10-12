// Global state management using Zustand
// Centralizes device data, command queue, and UI state

import { createStore } from "zustand/vanilla";
import type { StateCreator, StoreApi } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type {
  CachedStatus,
  DeviceState,
  QueuedCommand,
  UIState,
  CommandRecord,
  Notification,
  CommandRequest,
} from "../types/models";
import { getErrorMessage } from "../errors";

// ========================================
// STORE INTERFACES
// ========================================

interface DeviceStore {
  // Device state
  devices: Map<string, DeviceState>;

  // Configuration data (loaded once at startup)
  configurations: {
    dosers: Map<string, import('../api/configurations').DoserDevice>;
    lights: Map<string, import('../api/configurations').LightDevice>;
    isLoaded: boolean;
  };

  // Command queue
  commandQueue: QueuedCommand[];
  isProcessingCommands: boolean;

  // UI state
  ui: UIState;

  // Polling state
  polling: {
    isEnabled: boolean;
    intervalId: number | null;
    intervalMs: number;
  };

  // Actions
  actions: {
    // Configuration management
    loadConfigurations: () => Promise<void>;
    setConfigurations: (dosers: import('../api/configurations').DoserDevice[], lights: import('../api/configurations').LightDevice[]) => void;

    // Device management
    setDevices: (devices: CachedStatus[]) => void;
    updateDevice: (address: string, status: CachedStatus) => void;
    setDeviceLoading: (address: string, loading: boolean) => void;
    setDeviceError: (address: string, error: string | null) => void;

    // Command queue management
    queueCommand: (address: string, request: CommandRequest) => Promise<string>;
    processCommandQueue: () => Promise<void>;
    retryCommand: (commandId: string) => void;
    cancelCommand: (commandId: string) => void;
    clearCommandQueue: () => void;

    // UI state management
    setCurrentView: (view: UIState["currentView"]) => void;
    setGlobalError: (error: string | null) => void;
    addNotification: (notification: Omit<Notification, "id" | "timestamp">) => void;
    removeNotification: (id: string) => void;
    clearNotifications: () => void;

    // Data refresh
    initializeStore: () => Promise<void>;
    refreshDevices: () => Promise<void>;
    refreshDevice: (address: string) => Promise<void>;
    connectToDevice: (address: string) => Promise<void>;

    // Polling management (placeholder for future real-time updates)
    startPolling: (intervalMs?: number) => void;
    stopPolling: () => void;
    setPollingInterval: (intervalMs: number) => void;
  };
}

// ========================================
// STORE IMPLEMENTATION
// ========================================

const storeInitializer: StateCreator<DeviceStore> = (set, get) => ({
  // Initial state
  devices: new Map(),
  configurations: {
    dosers: new Map(),
    lights: new Map(),
    isLoaded: false,
  },
  commandQueue: [],
  isProcessingCommands: false,
  ui: {
    currentView: "dashboard",
    globalError: null,
    notifications: [],
  },
  polling: {
    isEnabled: false,
    intervalId: null,
    intervalMs: 30000, // Default 30 seconds
  },

  actions: {
      // Configuration management
      loadConfigurations: async () => {
        try {
          const { getDoserConfigurations, getLightConfigurations } = await import("../api/configurations");
          const [dosers, lights] = await Promise.all([
            getDoserConfigurations(),
            getLightConfigurations()
          ]);

          get().actions.setConfigurations(dosers, lights);
        } catch (error) {
          console.error("Failed to load configurations:", error);
          get().actions.setGlobalError("Failed to load device configurations");
        }
      },

      setConfigurations: (dosers, lights) => {
        const doserMap = new Map();
        const lightMap = new Map();

        dosers.forEach(doser => doserMap.set(doser.id, doser));
        lights.forEach(light => lightMap.set(light.id, light));

        set((state) => ({
          configurations: {
            dosers: doserMap,
            lights: lightMap,
            isLoaded: true,
          }
        }));

        // Update existing devices to include configuration data
        const devices = new Map(get().devices);
        devices.forEach((device, address) => {
          const config = doserMap.get(address) || lightMap.get(address);
          if (config) {
            devices.set(address, {
              ...device,
              configuration: config,
            });
          }
        });
        set({ devices });
      },

      // Device management
      setDevices: (devices) => {
        const deviceMap = new Map<string, DeviceState>();
        const { configurations } = get();

        devices.forEach((status) => {
          const existing = get().devices.get(status.address);
          const config = configurations.dosers.get(status.address) || configurations.lights.get(status.address);

          deviceMap.set(status.address, {
            address: status.address,
            status,
            configuration: config || null,
            lastUpdated: Date.now(),
            isLoading: existing?.isLoading ?? false,
            error: null,
          });
        });
        set({ devices: deviceMap });
      },

      updateDevice: (address, status) => {
        const devices = new Map(get().devices);
        const existing = devices.get(address);
        const { configurations } = get();
        const config = configurations.dosers.get(address) || configurations.lights.get(address);

        devices.set(address, {
          address,
          status,
          configuration: config || existing?.configuration || null,
          lastUpdated: Date.now(),
          isLoading: false,
          error: null,
        });
        set({ devices });
      },

      setDeviceLoading: (address, loading) => {
        const devices = new Map(get().devices);
        const existing = devices.get(address);
        if (existing) {
          devices.set(address, { ...existing, isLoading: loading });
          set({ devices });
        }
      },

      setDeviceError: (address, error) => {
        const devices = new Map(get().devices);
        const existing = devices.get(address);
        if (existing) {
          devices.set(address, { ...existing, error, isLoading: false });
          set({ devices });
        }
      },

      // Command queue management
      queueCommand: async (address, request) => {
        const commandId = `cmd_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const queuedCommand: QueuedCommand = {
          id: commandId,
          address,
          request: { ...request, id: request.id || commandId },
          queuedAt: Date.now(),
          retryCount: 0,
        };

        set((state) => ({
          commandQueue: [...state.commandQueue, queuedCommand],
        }));

        // Auto-process if not already processing
        if (!get().isProcessingCommands) {
          await get().actions.processCommandQueue();
        }

        return commandId;
      },

      processCommandQueue: async () => {
        const { commandQueue, isProcessingCommands, actions } = get();

        if (isProcessingCommands || commandQueue.length === 0) {
          return;
        }

        set({ isProcessingCommands: true });

        try {
          while (get().commandQueue.length > 0) {
            const [nextCommand, ...remaining] = get().commandQueue;
            set({ commandQueue: remaining });

            try {
              // Set device as loading
              actions.setDeviceLoading(nextCommand.address, true);

              // Execute command via API
              const { executeCommand } = await import("../api/commands");
              const result = await executeCommand(nextCommand.address, nextCommand.request);

              // Handle command result
              if (result.status === "success") {
                // Refresh device status if command was successful
                await actions.refreshDevice(nextCommand.address);
                actions.addNotification({
                  type: "success",
                  message: `Command completed successfully`,
                  autoHide: true,
                });
              } else if (result.status === "failed" || result.status === "timed_out") {
                // Command failed - use structured error information
                const errorMessage = getErrorMessage(result.error_code && result.error ? {
                  code: result.error_code as any,
                  message: result.error,
                  details: result.result as any || {}
                } : null);

                actions.setDeviceError(nextCommand.address, errorMessage);
                actions.addNotification({
                  type: "error",
                  message: errorMessage,
                  autoHide: false,
                });
              }

            } catch (error) {
              // Network/API error - this shouldn't happen in normal operation
              const errorMessage = error instanceof Error ? error.message : "Network error";
              actions.setDeviceError(nextCommand.address, errorMessage);
              actions.addNotification({
                type: "error",
                message: `Network error: ${errorMessage}`,
                autoHide: false,
              });
            } finally {
              actions.setDeviceLoading(nextCommand.address, false);
            }
          }
        } finally {
          set({ isProcessingCommands: false });
        }
      },

      retryCommand: (commandId) => {
        const { commandQueue } = get();
        const command = commandQueue.find(cmd => cmd.id === commandId);
        if (command) {
          const retryCommand = {
            ...command,
            retryCount: command.retryCount + 1,
            queuedAt: Date.now(),
          };
          set({
            commandQueue: commandQueue.filter(cmd => cmd.id !== commandId).concat(retryCommand),
          });
        }
      },

      cancelCommand: (commandId) => {
        set((state) => ({
          commandQueue: state.commandQueue.filter(cmd => cmd.id !== commandId),
        }));
      },

      clearCommandQueue: () => {
        set({ commandQueue: [] });
      },

      // UI state management
      setCurrentView: (view) => {
        set((state) => ({
          ui: { ...state.ui, currentView: view },
        }));
      },

      setGlobalError: (error) => {
        set((state) => ({
          ui: { ...state.ui, globalError: error },
        }));
      },

      addNotification: (notification) => {
        const id = `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const newNotification: Notification = {
          ...notification,
          id,
          timestamp: Date.now(),
        };

        set((state) => ({
          ui: {
            ...state.ui,
            notifications: [...state.ui.notifications, newNotification],
          },
        }));

        // Auto-remove after 5 seconds if autoHide is true
        if (notification.autoHide) {
          setTimeout(() => {
            get().actions.removeNotification(id);
          }, 5000);
        }
      },

      removeNotification: (id) => {
        set((state) => ({
          ui: {
            ...state.ui,
            notifications: state.ui.notifications.filter(n => n.id !== id),
          },
        }));
      },

      clearNotifications: () => {
        set((state) => ({
          ui: { ...state.ui, notifications: [] },
        }));
      },

    // Data refresh
    initializeStore: async () => {
      // Stage 1: Load configurations immediately (these load from cached backend data)
      await get().actions.loadConfigurations();

      // Stage 2: Load live status and overlay on configurations
      await get().actions.refreshDevices();

      // Stage 3: Start polling for real-time updates (placeholder)
      get().actions.startPolling();
    },

    refreshDevices: async () => {
      try {
        const { fetchJson } = await import("../api/http");
        const data = await fetchJson<{ [address: string]: CachedStatus }>("/api/status");
        const devices = Object.values(data) as CachedStatus[];
        get().actions.setDevices(devices);
        get().actions.setGlobalError(null);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to refresh devices";
        get().actions.setGlobalError(message);
        throw error;
      }
    },      refreshDevice: async (address) => {
        try {
          get().actions.setDeviceLoading(address, true);
          const { postJson } = await import("../api/http");
          await postJson(`/api/devices/${encodeURIComponent(address)}/status`, {});

          // Refresh all devices to get updated status
          await get().actions.refreshDevices();
        } catch (error) {
          const message = error instanceof Error ? error.message : "Failed to refresh device";
          get().actions.setDeviceError(address, message);
          throw error;
        }
      },

      connectToDevice: async (address) => {
        try {
          const { postJson } = await import("../api/http");
          await postJson(`/api/devices/${encodeURIComponent(address)}/connect`, {});
          get().actions.addNotification({
            type: "success",
            message: `Connected to device ${address}`,
            autoHide: true,
          });

          // Refresh devices after connection
          await get().actions.refreshDevices();
        } catch (error) {
          const message = error instanceof Error ? error.message : "Failed to connect to device";
          get().actions.addNotification({
            type: "error",
            message: `Connection failed: ${message}`,
            autoHide: true,
          });
          throw error;
        }
      },

      // Polling management (placeholder for future real-time updates)
      startPolling: (intervalMs = 30000) => {
        const { polling } = get();

        // Stop existing polling if running
        if (polling.intervalId) {
          clearInterval(polling.intervalId);
        }

        // Start new polling
        const intervalId = setInterval(() => {
          // Only poll if we have configurations loaded and devices
          const { configurations, devices } = get();
          if (configurations.isLoaded && devices.size > 0) {
            get().actions.refreshDevices().catch((error) => {
              console.warn("Polling refresh failed:", error);
              // Continue polling even if one refresh fails
            });
          }
        }, intervalMs);

        set((state) => ({
          polling: {
            ...state.polling,
            isEnabled: true,
            intervalId: intervalId as any, // TypeScript types for setInterval can be tricky
            intervalMs,
          }
        }));
      },

      stopPolling: () => {
        const { polling } = get();

        if (polling.intervalId) {
          clearInterval(polling.intervalId);
        }

        set((state) => ({
          polling: {
            ...state.polling,
            isEnabled: false,
            intervalId: null,
          }
        }));
      },

      setPollingInterval: (intervalMs) => {
        const { polling } = get();

        set((state) => ({
          polling: {
            ...state.polling,
            intervalMs,
          }
        }));

        // Restart polling with new interval if currently enabled
        if (polling.isEnabled) {
          get().actions.startPolling(intervalMs);
        }
      },
  },
});

const createDeviceStore = (): StoreApi<DeviceStore> =>
  createStore<DeviceStore>()(subscribeWithSelector(storeInitializer));

export const deviceStore = createDeviceStore();

// ========================================
// SELECTORS FOR EASY ACCESS
// ========================================

export const getDeviceStore = () => deviceStore;

export const useDevices = () =>
  Array.from(deviceStore.getState().devices.values());
export const useDevice = (address: string) =>
  deviceStore.getState().devices.get(address);
export const useConfigurations = () => deviceStore.getState().configurations;
export const usePolling = () => deviceStore.getState().polling;
export const useCommandQueue = () => deviceStore.getState().commandQueue;
export const useUI = () => deviceStore.getState().ui;
export const useActions = () => deviceStore.getState().actions;

// Device type selectors
export const useLightDevices = () =>
  Array.from(deviceStore.getState().devices.values()).filter(
    (device) => device.status?.device_type === "light",
  );

export const useDoserDevices = () =>
  Array.from(deviceStore.getState().devices.values()).filter(
    (device) => device.status?.device_type === "doser",
  );

// UI state selectors
export const useCurrentView = () => deviceStore.getState().ui.currentView;
export const useNotifications = () => deviceStore.getState().ui.notifications;
export const useGlobalError = () => deviceStore.getState().ui.globalError;
