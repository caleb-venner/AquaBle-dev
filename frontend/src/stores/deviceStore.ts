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

  // Command queue
  commandQueue: QueuedCommand[];
  isProcessingCommands: boolean;

  // UI state
  ui: UIState;

  // Actions
  actions: {
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
    refreshDevices: () => Promise<void>;
    refreshDevice: (address: string) => Promise<void>;
    connectToDevice: (address: string) => Promise<void>;
  };
}

// ========================================
// STORE IMPLEMENTATION
// ========================================

const storeInitializer: StateCreator<DeviceStore> = (set, get) => ({
  // Initial state
  devices: new Map(),
  commandQueue: [],
  isProcessingCommands: false,
  ui: {
    currentView: "dashboard",
    globalError: null,
    notifications: [],
  },

  actions: {
      // Device management
      setDevices: (devices) => {
        const deviceMap = new Map<string, DeviceState>();
        devices.forEach((status) => {
          const existing = get().devices.get(status.address);
          deviceMap.set(status.address, {
            address: status.address,
            status,
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
        devices.set(address, {
          address,
          status,
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
      },

      refreshDevice: async (address) => {
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
export const useCommandQueue = () => deviceStore.getState().commandQueue;
export const useUI = () => deviceStore.getState().ui;
export const useActions = () => deviceStore.getState().actions;

// Device type selectors
export const useLightDevices = () =>
  Array.from(deviceStore.getState().devices.values()).filter(
    (device) => device.status.device_type === "light",
  );

export const useDoserDevices = () =>
  Array.from(deviceStore.getState().devices.values()).filter(
    (device) => device.status.device_type === "doser",
  );

// UI state selectors
export const useCurrentView = () => deviceStore.getState().ui.currentView;
export const useNotifications = () => deviceStore.getState().ui.notifications;
export const useGlobalError = () => deviceStore.getState().ui.globalError;
