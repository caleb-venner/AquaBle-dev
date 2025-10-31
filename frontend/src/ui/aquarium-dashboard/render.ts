/**
 * Main dashboard rendering functions
 */

import { deviceStore } from "../../stores/deviceStore";
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
      ${renderFooter()}
    </div>
  `;
}

/**
 * Render the dashboard header
 */
function renderHeader(): string {
  const zustandState = deviceStore.getState();
  const isRefreshing = Array.from(zustandState.devices.values()).some(d => d.isLoading);
  return `
    <header class="prod-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-title">
            <h1>AquaBle</h1>
          </div>
        </div>
        <div class="header-actions">
          <div class="theme-toggle-container">
            <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 24 24" class="toggle-icon sun-icon" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg"><path fill="none" d="M0 0h24v24H0z"></path><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58a.996.996 0 0 0-1.41 0 .996.996 0 0 0 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37a.996.996 0 0 0-1.41 0 .996.996 0 0 0 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0a.996.996 0 0 0 0-1.41l-1.06-1.06zm1.06-10.96a.996.996 0 0 0 0-1.41.996.996 0 0 0-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36a.996.996 0 0 0 0-1.41.996.996 0 0 0-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"></path></svg>
            <div
              class="theme-toggle"
              onclick="window.toggleTheme()"
              title="Toggle Dark Mode"
              role="button"
              tabindex="0"
              aria-label="Toggle dark mode"
            >
              <div id="theme-toggle-knob" class="theme-knob ${(() => {
                try {
                  return localStorage.getItem('theme') === 'dark' ? 'on' : '';
                } catch (e) {
                  return '';
                }
              })()}" ></div>
            </div>
            <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 24 24" class="toggle-icon moon-icon" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg"><path fill="none" d="M0 0h24v24H0z"></path><path d="M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.389 5.389 0 0 1-4.4 2.26 5.403 5.403 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1z"></path></svg>
          </div>
          <a href="/hassio/addon/self_slug/config" class="btn btn-primary" title="Addon Settings">
            Plugin Settings
          </a>
        </div>
      </div>
    </header>
  `;
}

/**
 * Render the navigation tabs
 */
function renderNavigation(): string {
  const zustandState = deviceStore.getState();

  return `
    <nav class="prod-nav">
      <div class="nav-content">
        <button
          class="nav-tab ${zustandState.ui.currentView === "overview" ? "active" : ""}"
          onclick="window.switchTab('overview')"
        >
          Overview
        </button>
      </div>
    </nav>
  `;
}

/**
 * Render the main content area
 */
function renderContent(): string {
  const zustandState = deviceStore.getState();

  if (zustandState.ui.globalError) {
    return `
      <div class="error-state">
        <div class="error-icon">❌</div>
        <h2>Error Loading Dashboard</h2>
        <p>${zustandState.ui.globalError}</p>
        <button class="btn btn-primary" onclick="window.handleRefreshAll()">
          Try Again
        </button>
      </div>
    `;
  }

  return `
    <div class="tab-panel ${zustandState.ui.currentView === "overview" ? "active" : ""}" id="overview-panel">
      ${renderOverviewTab()}
    </div>
    <div class="tab-panel ${zustandState.ui.currentView === "dev" ? "active" : ""}" id="dev-panel">
      ${renderDevTab()}
    </div>
  `;
}

/**
 * Render the dashboard footer
 */
function renderFooter(): string {
  return `
    <footer class="prod-footer">
      <div class="footer-content">
        <a href="/tests/test-hub.html" target="_blank" class="footer-link">
          Test
        </a>
      </div>
    </footer>
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
