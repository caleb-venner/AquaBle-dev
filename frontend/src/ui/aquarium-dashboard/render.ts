/**
 * Main dashboard rendering functions
 */

import { getDashboardState } from "./state";
import { renderOverviewTab } from "./tabs/overview-tab";
import { renderDevTab } from "./tabs/dev-tab";

/**
 * Main render function for the production dashboard
 */
export function renderProductionDashboard(): string {
  return `
    <div class="production-dashboard">
      ${renderHeader()}
      ${renderNavigation()}
      <main class="prod-main">
        ${renderContent()}
      </main>
    </div>
  `;
}

/**
 * Render the dashboard header
 */
function renderHeader(): string {
  const state = getDashboardState();

  return `
    <header class="prod-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-title">
            <h1>Aquarium BLE Device Manager</h1>
            <p class="header-subtitle">Production Dashboard - Device Status Monitoring (Read-Only)</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-primary" onclick="window.handleScanDevices()">
            Scan & Connect
          </button>
          <button class="btn btn-secondary" onclick="window.handleRefreshAll()" ${state.isRefreshing ? 'disabled' : ''}>
            ${state.isRefreshing ? '<span class="scan-spinner"></span> Refreshing...' : 'Refresh All'}
          </button>
        </div>
      </div>
    </header>
  `;
}

/**
 * Render the navigation tabs
 */
function renderNavigation(): string {
  const state = getDashboardState();

  return `
    <nav class="prod-nav">
      <div class="nav-content">
        <button
          class="nav-tab ${state.currentTab === "overview" ? "active" : ""}"
          onclick="window.switchTab('overview')"
        >
          Overview
        </button>
        <button
          class="nav-tab ${state.currentTab === "dev" ? "active" : ""}"
          onclick="window.switchTab('dev')"
        >
          Dev
        </button>
      </div>
    </nav>
  `;
}

/**
 * Render the main content area
 */
function renderContent(): string {
  const state = getDashboardState();

  if (state.error) {
    return `
      <div class="error-state">
        <div class="error-icon">❌</div>
        <h2>Error Loading Dashboard</h2>
        <p>${state.error}</p>
        <button class="btn btn-primary" onclick="window.handleRefreshAll()">
          Try Again
        </button>
      </div>
    `;
  }

  return `
    <div class="tab-panel ${state.currentTab === "overview" ? "active" : ""}" id="overview-panel">
      ${renderOverviewTab()}
    </div>
    <div class="tab-panel ${state.currentTab === "dev" ? "active" : ""}" id="dev-panel">
      ${renderDevTab()}
    </div>
  `;
}

/**
 * Refresh the dashboard UI
 */
export function refreshDashboard(): void {
  const dashboardElement = document.querySelector('.production-dashboard');
  if (dashboardElement) {
    dashboardElement.outerHTML = renderProductionDashboard();
  }
}
