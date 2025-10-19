/**
 * Centralized polling service for device status
 * Ensures only one active polling loop runs instead of multiple component-level polls
 */

import { getDeviceStatus } from "../../../api/devices";
import { setDeviceStatus, getDashboardState, markDeviceStable, markDeviceUnstable } from "../state";

interface PollingState {
  isActive: boolean;
  intervalId: number | null;
  intervalMs: number;
  lastPollTime: number;
  failureCount: number;
  maxFailures: number;
}

class PollingService {
  private state: PollingState = {
    isActive: false,
    intervalId: null,
    intervalMs: 30000, // Default 30 seconds
    lastPollTime: 0,
    failureCount: 0,
    maxFailures: 5, // Stop polling after 5 consecutive failures
  };

  private subscribers: ((status: any) => void)[] = [];

  /**
   * Start polling device status at specified interval
   */
  startPolling(intervalMs: number = 30000): void {
    if (this.state.isActive) {
      console.log("ℹ️  Polling already active");
      return;
    }

    this.state.intervalMs = intervalMs;
    this.state.isActive = true;
    this.state.failureCount = 0;

    console.log(`🔄 Starting device status polling (interval: ${intervalMs}ms)`);

    // Initial poll immediately
    this.poll();

    // Set up interval for subsequent polls
    this.state.intervalId = window.setInterval(() => {
      this.poll();
    }, intervalMs);
  }

  /**
   * Stop polling
   */
  stopPolling(): void {
    if (!this.state.isActive) {
      console.log("ℹ️  Polling not active");
      return;
    }

    if (this.state.intervalId !== null) {
      clearInterval(this.state.intervalId);
      this.state.intervalId = null;
    }

    this.state.isActive = false;
    this.state.failureCount = 0;
    console.log("⏸️  Device status polling stopped");
  }

  /**
   * Change polling interval
   */
  setInterval(intervalMs: number): void {
    this.state.intervalMs = intervalMs;
    if (this.state.isActive) {
      // Restart with new interval
      this.stopPolling();
      this.startPolling(intervalMs);
    }
  }

  /**
   * Subscribe to polling updates
   */
  subscribe(callback: (status: any) => void): () => void {
    this.subscribers.push(callback);
    // Return unsubscribe function
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  /**
   * Execute a single poll
   */
  private async poll(): Promise<void> {
    try {
      this.state.lastPollTime = Date.now();
      const status = await getDeviceStatus();

      // Reset failure count on successful poll
      this.state.failureCount = 0;

      // Update local state
      setDeviceStatus(status);

      // Track connection stability
      const previousState = getDashboardState();
      const previousStatus = previousState.deviceStatus;

      Object.entries(status).forEach(([address, deviceStatus]: [string, any]) => {
        const previousDeviceStatus = previousStatus?.[address];

        if (previousDeviceStatus?.connected && !deviceStatus.connected) {
          markDeviceUnstable(address);
        } else if (deviceStatus.connected && previousDeviceStatus?.connected) {
          markDeviceStable(address);
        }
      });

      // Notify subscribers
      this.subscribers.forEach(callback => callback(status));

      console.log(`✅ Status poll completed (${Object.keys(status).length} devices)`);
    } catch (error) {
      this.state.failureCount++;
      console.error(`❌ Status poll failed (${this.state.failureCount}/${this.state.maxFailures}):`, error);

      // Stop polling after too many failures
      if (this.state.failureCount >= this.state.maxFailures) {
        console.error("⚠️  Too many polling failures, stopping polling service");
        this.stopPolling();
      }
    }
  }

  /**
   * Get current polling state
   */
  getState(): Readonly<PollingState> {
    return Object.freeze({ ...this.state });
  }

  /**
   * Force immediate poll (useful for manual refresh)
   */
  async forcePoll(): Promise<void> {
    if (!this.state.isActive) {
      console.log("ℹ️  Polling not active, starting temporary poll");
    }
    await this.poll();
  }
}

export const pollingService = new PollingService();

/**
 * Initialize polling on dashboard load
 */
export function initializePolling(intervalMs: number = 30000): void {
  pollingService.startPolling(intervalMs);
}

/**
 * Cleanup polling on dashboard unload
 */
export function cleanupPolling(): void {
  pollingService.stopPolling();
}

/**
 * Get debug info about polling state
 */
export function getPollingDebugInfo(): Record<string, any> {
  const state = pollingService.getState();
  return {
    isActive: state.isActive,
    intervalMs: state.intervalMs,
    lastPollTime: state.lastPollTime,
    failureCount: state.failureCount,
    subscriberCount: (pollingService as any).subscribers?.length || 0,
  };
}
