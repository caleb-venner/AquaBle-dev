/**
 * Home Assistant tab rendering
 */

import { renderHAControls, attachHAHandlers } from "../../ha-controls";

/**
 * Render the Home Assistant tab - shows HA entity controls
 */
export function renderHATab(): string {
  const html = `
    <div class="ha-tab-container" id="ha-controls-root">
      ${renderHAControls()}
    </div>
  `;
  
  // Attach handlers after a brief delay to ensure DOM is ready
  setTimeout(() => {
    const container = document.getElementById('ha-controls-root');
    if (container) {
      attachHAHandlers(container);
    }
  }, 0);
  
  return html;
}
