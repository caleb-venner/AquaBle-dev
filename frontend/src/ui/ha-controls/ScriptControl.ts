/**
 * Script Control Component
 * 
 * Displays a script entity with an execute button.
 * Scripts are stateless - they only show an execution button.
 */

import { useHAStore, type HAEntity } from '../../stores/haStore';

export function renderScriptControl(entity: HAEntity): string {
  return `
    <div class="ha-entity-card script-control" data-entity-id="${entity.entity_id}">
      <div class="entity-header">
        <h3>${entity.label}</h3>
        <span class="entity-id">${entity.entity_id}</span>
      </div>
      <div class="entity-content">
        <div class="state-display">
          <span class="state-label">Type:</span>
          <span class="state-value">SCRIPT</span>
        </div>
        <div class="entity-controls">
          <button 
            class="btn-execute" 
            data-action="execute"
            data-entity-id="${entity.entity_id}"
          >
            Execute
          </button>
        </div>
      </div>
    </div>
  `;
}

export function attachScriptHandlers(container: HTMLElement) {
  const executeButtons = container.querySelectorAll<HTMLButtonElement>('[data-action="execute"]');
  
  executeButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const entityId = button.dataset.entityId;
      if (!entityId) return;
      
      button.disabled = true;
      button.textContent = 'Executing...';
      
      try {
        await useHAStore.getState().executeScript(entityId);
        
        // Show brief success feedback
        button.textContent = 'Executed!';
        setTimeout(() => {
          button.textContent = 'Execute';
        }, 2000);
      } catch (error) {
        button.textContent = 'Failed';
        setTimeout(() => {
          button.textContent = 'Execute';
        }, 2000);
      } finally {
        button.disabled = false;
      }
    });
  });
}
