/**
 * Switch Control Component
 * 
 * Displays a switch entity with its current state and toggle button.
 */

import { useHAStore, type HAEntity, type EntityState } from '../../stores/haStore';

export function renderSwitchControl(entity: HAEntity, state: EntityState | undefined): string {
  const currentState = state?.state || 'unknown';
  const isOn = currentState === 'on';
  const isOff = currentState === 'off';
  const stateClass = isOn ? 'state-on' : isOff ? 'state-off' : 'state-unknown';
  
  return `
    <div class="ha-entity-card switch-control" data-entity-id="${entity.entity_id}">
      <div class="entity-header">
        <h3>${entity.label}</h3>
      </div>
      <div class="entity-content">
        <div class="state-display ${stateClass}">
          <span class="state-label">State:</span>
          <span class="state-value">${currentState.toUpperCase()}</span>
        </div>
        <div class="entity-controls">
          <button 
            class="btn-toggle" 
            data-action="toggle"
            data-entity-id="${entity.entity_id}"
          >
            Toggle
          </button>
        </div>
      </div>
    </div>
  `;
}

export function attachSwitchHandlers(container: HTMLElement) {
  const toggleButtons = container.querySelectorAll<HTMLButtonElement>('[data-action="toggle"]');
  
  toggleButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const entityId = button.dataset.entityId;
      if (!entityId) return;
      
      button.disabled = true;
      try {
        await useHAStore.getState().toggleSwitch(entityId);
      } finally {
        button.disabled = false;
      }
    });
  });
}
