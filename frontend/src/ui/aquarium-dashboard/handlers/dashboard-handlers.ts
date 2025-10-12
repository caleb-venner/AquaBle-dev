/**
 * Dashboard event handlers - Read-only dashboard with no scanning/connection capabilities
 */

import { getDashboardState, setCurrentTab } from "../state";
import type { DashboardTab } from "../types";
import { loadAllDashboardData } from "../services/data-service";

// Dashboard refresh handler
export async function handleRefreshAll(): Promise<void> {
  try {
    await loadAllDashboardData();
    // Refresh the dashboard UI
    const { refreshDashboard } = await import("../render");
    refreshDashboard();
  } catch (error) {
    console.error('Failed to refresh dashboard:', error);
  }
}

// Tab switching handler
export async function switchTab(tabName: string): Promise<void> {
  setCurrentTab(tabName as DashboardTab);

  // Update URL hash for bookmarking
  window.location.hash = tabName;

  // Refresh dashboard to show new tab
  const { refreshDashboard } = await import("../render");
  refreshDashboard();
}
