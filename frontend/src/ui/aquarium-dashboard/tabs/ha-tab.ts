/**
 * Home Assistant tab rendering
 */

import { renderHAControls } from "../../ha-controls";

/**
 * Render the Home Assistant tab - shows HA entity controls
 */
export function renderHATab(): string {
  return `
    <div class="ha-tab-container" id="ha-controls-root">
      ${renderHAControls()}
    </div>
  `;
}
