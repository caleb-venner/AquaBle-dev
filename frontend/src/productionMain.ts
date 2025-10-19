/**
 * Production Dashboard - Main Entry Point
 *
 * This is the production-ready dashboard that will be the foundation for the first release.
 * Features:
 * - Device configuration management (view, edit, delete)
 * - Saved configuration profiles
 * - Enhanced device management with naming and grouping
 * - Clean, professional UI
 */

import { renderProductionDashboard, initializeDashboardHandlers } from "./ui/aquarium-dashboard/dashboard";
import { createNotificationSystem } from "./ui/notifications";
import { setupStateSubscriptions } from "./ui/stateSubscriptions";
import "./ui/dashboard.css";

// Guard against double initialization (e.g., from Vite HMR)
let isInitializing = false;
let isInitialized = false;

// Initialize the production dashboard
async function init() {
  console.log("productionMain.init() called");
  
  if (isInitializing) {
    console.warn("Already initializing, skipping duplicate call");
    return;
  }
  
  if (isInitialized) {
    console.warn("Already initialized, skipping duplicate call");
    return;
  }
  
  isInitializing = true;
  
  try {
    console.log("Initializing Production Dashboard...");

    const appElement = document.getElementById("app");
    if (!appElement) {
      throw new Error("App element not found");
    }

    // Initialize theme from localStorage
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      document.documentElement.className = 'dark-theme';
    }

    // Initialize notification system
    createNotificationSystem();

    // Initialize dashboard handlers
    initializeDashboardHandlers();

    // Render the dashboard
    console.log("Rendering dashboard HTML...");
    appElement.innerHTML = renderProductionDashboard();

    // Load dashboard data BEFORE setting up subscriptions to avoid duplicate loads
    console.log("Loading dashboard data...");
    const { loadAllDashboardData, refreshDashboard } = await import("./ui/aquarium-dashboard/dashboard");
    await loadAllDashboardData();
    console.log("Dashboard data loaded");

    // Re-render dashboard with loaded data
    console.log("Refreshing dashboard with loaded data...");
    refreshDashboard();

    // Setup state subscriptions for automatic updates AFTER initial load completes
    console.log("Setting up state subscriptions...");
    setupStateSubscriptions();

    console.log("Production Dashboard initialized successfully");
    isInitialized = true;
  } catch (error) {
    console.error("Failed to initialize Production Dashboard:", error);

    const appElement = document.getElementById("app");
    if (appElement) {
      appElement.innerHTML = `
        <div style="padding: 40px; text-align: center;">
          <h1 style="color: #dc2626;">Failed to Load Dashboard</h1>
          <p style="color: #64748b;">${error instanceof Error ? error.message : String(error)}</p>
          <button
            onclick="location.reload()"
            style="padding: 10px 20px; margin-top: 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;"
          >
            Retry
          </button>
        </div>
      `;
    }
  } finally {
    isInitializing = false;
  }
}

// Start the application when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
