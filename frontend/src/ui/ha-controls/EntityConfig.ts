/**
 * Entity Configuration Component
 * 
 * Form for adding and removing Home Assistant entities.
 */

import { useHAStore, type EntityType } from '../../stores/haStore';

export function renderEntityConfig(): string {
  return `
    <div class="ha-config-panel">
      <h3>Add Entity</h3>
      <form id="add-entity-form" class="entity-form">
        <div class="form-group">
          <label for="entity-id-input">Entity ID</label>
          <input 
            type="text" 
            id="entity-id-input" 
            placeholder="switch.aquarium_pump"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="entity-label-input">Label</label>
          <input 
            type="text" 
            id="entity-label-input" 
            placeholder="Main Pump"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="entity-type-select">Type</label>
          <select id="entity-type-select" required>
            <option value="switch">Switch</option>
            <option value="script">Script</option>
          </select>
        </div>
        
        <button type="submit" class="btn-primary">Add Entity</button>
      </form>
    </div>
  `;
}

export function attachConfigHandlers(container: HTMLElement) {
  const form = container.querySelector<HTMLFormElement>('#add-entity-form');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const entityIdInput = form.querySelector<HTMLInputElement>('#entity-id-input');
    const labelInput = form.querySelector<HTMLInputElement>('#entity-label-input');
    const typeSelect = form.querySelector<HTMLSelectElement>('#entity-type-select');
    
    if (!entityIdInput || !labelInput || !typeSelect) return;
    
    const entityId = entityIdInput.value.trim();
    const label = labelInput.value.trim();
    const type = typeSelect.value as EntityType;
    
    if (!entityId || !label) return;
    
    try {
      await useHAStore.getState().addEntity(entityId, label, type);
      
      // Clear form on success
      entityIdInput.value = '';
      labelInput.value = '';
      typeSelect.selectedIndex = 0;
    } catch (error) {
      console.error('Failed to add entity:', error);
    }
  });
}
