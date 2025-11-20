/**
 * Entity List Component
 * 
 * Main component that displays all configured Home Assistant entities.
 */

import { useHAStore } from '../../stores/haStore';
import { renderSwitchControl, attachSwitchHandlers } from './SwitchControl';
import { renderScriptControl, attachScriptHandlers } from './ScriptControl';
import { renderEntityConfig, attachConfigHandlers } from './EntityConfig';

export function renderHAControls(): string {
  const { available, loading, error, entities, entityStates } = useHAStore.getState();
  
  if (!available) {
    return `
      <div class="ha-controls-container">
        <div class="ha-unavailable">
          <h2>Home Assistant Integration</h2>
          <p>Home Assistant integration is not available.</p>
          <p class="note">This feature requires running as a Home Assistant add-on.</p>
        </div>
      </div>
    `;
  }
  
  if (loading && entities.length === 0) {
    return `
      <div class="ha-controls-container">
        <div class="ha-loading">
          <h2>Home Assistant Controls</h2>
          <p>Loading entities...</p>
        </div>
      </div>
    `;
  }
  
  const errorHtml = error ? `
    <div class="ha-error">
      ${error}
    </div>
  ` : '';
  
  const entitiesHtml = entities.length > 0 ? `
    <div class="ha-entities-grid">
      ${entities.map(entity => {
        if (entity.type === 'switch') {
          return renderSwitchControl(entity, entityStates[entity.entity_id]);
        } else {
          return renderScriptControl(entity);
        }
      }).join('')}
    </div>
  ` : `
    <div class="ha-empty">
      <p>No entities configured yet.</p>
      <p class="note">Add your first Home Assistant entity below.</p>
    </div>
  `;
  
  return `
    <div class="ha-controls-container">
      <div class="ha-header">
        <h2>Home Assistant Controls</h2>
        <button id="refresh-ha-button" class="btn-refresh">Refresh</button>
      </div>
      
      ${errorHtml}
      
      <div class="ha-content">
        ${entitiesHtml}
        
        <div class="ha-config-section">
          ${renderEntityConfig()}
        </div>
      </div>
    </div>
  `;
}

export function attachHAHandlers(container: HTMLElement) {
  // Attach handlers for switch controls
  attachSwitchHandlers(container);
  
  // Attach handlers for script controls
  attachScriptHandlers(container);
  
  // Attach handlers for configuration form
  attachConfigHandlers(container);
  
  // Attach refresh button handler
  const refreshButton = container.querySelector<HTMLButtonElement>('#refresh-ha-button');
  if (refreshButton) {
    refreshButton.addEventListener('click', async () => {
      refreshButton.disabled = true;
      try {
        await useHAStore.getState().fetchConfig();
      } finally {
        refreshButton.disabled = false;
      }
    });
  }
  
  // Attach delete handlers for entities
  const deleteButtons = container.querySelectorAll<HTMLButtonElement>('[data-action="delete"]');
  deleteButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const entityId = button.dataset.entityId;
      if (!entityId) return;
      
      if (!confirm(`Remove entity ${entityId}?`)) return;
      
      button.disabled = true;
      try {
        await useHAStore.getState().removeEntity(entityId);
      } finally {
        button.disabled = false;
      }
    });
  });
}

/**
 * Initialize Home Assistant controls
 */
export async function initializeHAControls(containerId: string) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Container ${containerId} not found`);
    return;
  }
  
  // Check availability
  await useHAStore.getState().checkAvailability();
  
  // Fetch config if available
  if (useHAStore.getState().available) {
    await useHAStore.getState().fetchConfig();
  }
  
  // Subscribe to store changes for re-rendering
  useHAStore.subscribe(() => {
    container.innerHTML = renderHAControls();
    attachHAHandlers(container);
  });
  
  // Initial render
  container.innerHTML = renderHAControls();
  attachHAHandlers(container);
}
