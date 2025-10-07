// Modern Dashboard - Standalone Entry Point
// This is completely separate from the legacy dashboard system

import { createNotificationSystem } from "./ui/notifications";
import { setupModernDashboard, renderModernDashboard } from "./ui/modernDashboard";
import { setupStateSubscriptions } from "./ui/stateSubscriptions";
import { useActions } from "./stores/deviceStore";

// Debug function to update status
function updateDebugStatus(message: string): void {
  const debug = document.getElementById('debug-status');
  if (debug) {
    const stepCount = parseInt(debug.textContent?.match(/Step (\d+):/)?.[1] || '0') + 1;
    debug.textContent = `Step ${stepCount}: ${message}`;
  }
  console.log(`🚀 Modern Dashboard: ${message}`);
}

// Error handling function
function showError(error: any): void {
  updateDebugStatus(`ERROR: ${error.message}`);
  const app = document.querySelector<HTMLDivElement>("#app");
  if (app) {
    app.innerHTML = `
      <div class="error">
        <h2>Failed to Load Modern Dashboard</h2>
        <p><strong>Error:</strong> ${error.message}</p>
        <details>
          <summary>Technical Details</summary>
          <pre>${error.stack}</pre>
        </details>
        <p>
          <a href="/index.html">← Back to Legacy Dashboard</a> |
          <button onclick="location.reload()">Retry</button>
        </p>
      </div>
    `;
  }
}

// Standalone modern dashboard application
document.addEventListener("DOMContentLoaded", async () => {
  updateDebugStatus("DOMContentLoaded event fired");

  try {
    updateDebugStatus("Starting initialization...");

    // Initialize the app container with modern dashboard layout
    updateDebugStatus("Initializing layout...");
    initializeModernLayout();

    // Initialize notification system
    updateDebugStatus("Creating notification system...");
    createNotificationSystem();

    // Setup the modern dashboard
    updateDebugStatus("Setting up dashboard...");
    setupModernDashboard();

    // Setup state subscriptions for real-time updates
    updateDebugStatus("Setting up state subscriptions...");
    setupStateSubscriptions();

    // Load initial data
    updateDebugStatus("Loading initial device data...");
    const { refreshDevices } = useActions();
    try {
      await refreshDevices();
      updateDebugStatus("✅ Initial device data loaded");
    } catch (error) {
      updateDebugStatus(`⚠️ Failed to load initial data: ${error}`);
      console.warn("⚠️ Failed to load initial device data:", error);
    }

    // Render the dashboard
    updateDebugStatus("Rendering dashboard...");
    renderDashboard();

    updateDebugStatus("🎉 Modern Dashboard ready!");

    // Hide debug status after success
    setTimeout(() => {
      const debug = document.getElementById('debug-status');
      if (debug) debug.style.display = 'none';
    }, 2000);

  } catch (error) {
    console.error("❌ Failed to initialize Modern Dashboard:", error);
    showError(error);
  }
});

function initializeModernLayout(): void {
  const app = document.querySelector<HTMLDivElement>("#app");
  if (!app) {
    console.error("App container not found");
    return;
  }

  // Create standalone modern dashboard layout
  app.innerHTML = `
    <div class="modern-app">
      <header class="modern-header">
        <div class="header-content">
          <div class="brand">
            <h1>🏠 Chihiros Device Manager</h1>
            <span class="version">Modern Dashboard v2.0</span>
          </div>
          <div class="header-actions">
            <a class="btn btn-sm btn-secondary" href="/index.html" title="Open Legacy Dashboard">
              Dev Tools
            </a>
            <a class="btn btn-sm btn-secondary" href="/test" title="Open Testing Utilities">
              Test Tools
            </a>
          </div>
        </div>
      </header>

      <main class="modern-main">
        <div id="modern-dashboard-content">
          <div class="loading-state">
            <div class="loading-spinner"></div>
            <p>Initializing dashboard...</p>
          </div>
        </div>
      </main>

      <footer class="modern-footer">
        <div class="footer-content">
          <span class="footer-info">Modern Dashboard • Real-time Updates • TypeScript</span>
          <div class="footer-links">
            <a href="https://github.com/caleb-venner/chihiros-device-manager" target="_blank">GitHub</a>
            <span>•</span>
            <button class="link-button" onclick="showKeyboardShortcuts()">Shortcuts</button>
          </div>
        </div>
      </footer>
    </div>
  `;
}

function renderDashboard(): void {
  const container = document.getElementById("modern-dashboard-content");
  if (container) {
    container.innerHTML = renderModernDashboard();
  }
}

// Global functions for header actions
(window as any).showKeyboardShortcuts = () => {
  const { addNotification } = useActions();
  addNotification({
    type: "info",
    message: "Keyboard shortcuts: R - Refresh All, S - Scan Devices, Esc - Clear Notifications",
    autoHide: false
  });
};

// Keyboard shortcuts
document.addEventListener("keydown", (event) => {
  const { refreshDevices, scanForDevices, clearNotifications } = useActions();

  switch (event.key.toLowerCase()) {
    case 'r':
      if (event.ctrlKey || event.metaKey) return; // Don't interfere with browser refresh
      event.preventDefault();
      refreshDevices().catch(console.error);
      break;
    case 's':
      if (event.ctrlKey || event.metaKey) return; // Don't interfere with save
      event.preventDefault();
      scanForDevices().catch(console.error);
      break;
    case 'escape':
      event.preventDefault();
      clearNotifications();
      break;
  }
});

// Auto-update dashboard when store changes
let updateTimeout: number | null = null;
export function updateModernDashboard(): void {
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }

  updateTimeout = window.setTimeout(() => {
    renderDashboard();
    updateTimeout = null;
  }, 100);
}

// Make update function globally available for stateSubscriptions
(window as any).updateModernDashboard = updateModernDashboard;

// Listen for dashboard update requests from state subscriptions
document.addEventListener('dashboard-update-requested', () => {
  updateModernDashboard();
});
