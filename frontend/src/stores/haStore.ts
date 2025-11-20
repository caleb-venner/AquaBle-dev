/**
 * Home Assistant Store
 * 
 * Manages state and actions for Home Assistant entity control and configuration.
 */

import { createStore } from 'zustand/vanilla';

// ============================================================================
// Types
// ============================================================================

export type EntityType = 'switch' | 'script';

export interface HAEntity {
  entity_id: string;
  label: string;
  type: EntityType;
}

export interface EntityState {
  state: string;
  attributes: Record<string, any>;
  last_changed?: string;
  last_updated?: string;
}

interface HAStore {
  // State
  available: boolean;
  loading: boolean;
  error: string | null;
  entities: HAEntity[];
  entityStates: Record<string, EntityState>;
  
  // Actions
  checkAvailability: () => Promise<void>;
  fetchConfig: () => Promise<void>;
  fetchEntityState: (entityId: string) => Promise<void>;
  toggleSwitch: (entityId: string) => Promise<void>;
  executeScript: (entityId: string) => Promise<void>;
  addEntity: (entityId: string, label: string, type: EntityType) => Promise<void>;
  removeEntity: (entityId: string) => Promise<void>;
  updateEntityState: (entityId: string, state: EntityState) => void;
  setError: (error: string | null) => void;
}

// ============================================================================
// Store Implementation
// ============================================================================

export const haStore = createStore<HAStore>((set, get) => ({
  // Initial state
  available: false,
  loading: false,
  error: null,
  entities: [],
  entityStates: {},

  // Check if Home Assistant integration is available
  checkAvailability: async () => {
    try {
      const response = await fetch('api/ha/status');
      const data = await response.json();
      set({ available: data.available, error: null });
    } catch (error) {
      console.error('Error checking HA availability:', error);
      set({ available: false, error: 'Failed to check Home Assistant availability' });
    }
  },

  // Fetch configured entities
  fetchConfig: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('api/ha/config');
      if (!response.ok) {
        throw new Error(`Failed to fetch config: ${response.statusText}`);
      }
      const entities = await response.json();
      set({ entities, loading: false });
      
      // Fetch initial state for all switch entities
      for (const entity of entities) {
        if (entity.type === 'switch') {
          get().fetchEntityState(entity.entity_id);
        }
      }
    } catch (error) {
      console.error('Error fetching HA config:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch configuration',
        loading: false 
      });
    }
  },

  // Fetch state for a specific entity
  fetchEntityState: async (entityId: string) => {
    try {
      const response = await fetch(`api/ha/entity/${encodeURIComponent(entityId)}`);
      if (!response.ok) {
        if (response.status === 404) {
          console.warn(`Entity not found: ${entityId}`);
          return;
        }
        throw new Error(`Failed to fetch entity state: ${response.statusText}`);
      }
      const state = await response.json();
      set((prev) => ({
        entityStates: {
          ...prev.entityStates,
          [entityId]: state
        }
      }));
    } catch (error) {
      console.error(`Error fetching state for ${entityId}:`, error);
    }
  },

  // Toggle a switch entity
  toggleSwitch: async (entityId: string) => {
    set({ error: null });
    try {
      const response = await fetch('api/ha/switch/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to toggle switch: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Update state from response
      if (result.state) {
        set((prev) => ({
          entityStates: {
            ...prev.entityStates,
            [entityId]: result.state
          }
        }));
      } else {
        // Fallback: refetch state
        await get().fetchEntityState(entityId);
      }
    } catch (error) {
      console.error(`Error toggling switch ${entityId}:`, error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to toggle switch'
      });
    }
  },

  // Execute a script entity
  executeScript: async (entityId: string) => {
    set({ error: null });
    try {
      const response = await fetch('api/ha/script/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to execute script: ${response.statusText}`);
      }
      
      console.log(`Successfully executed script: ${entityId}`);
    } catch (error) {
      console.error(`Error executing script ${entityId}:`, error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to execute script'
      });
    }
  },

  // Add entity to configuration
  addEntity: async (entityId: string, label: string, type: EntityType) => {
    set({ error: null });
    try {
      const response = await fetch('api/ha/config/entity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId, label, type })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to add entity: ${response.statusText}`);
      }
      
      // Refresh config
      await get().fetchConfig();
    } catch (error) {
      console.error(`Error adding entity ${entityId}:`, error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to add entity'
      });
    }
  },

  // Remove entity from configuration
  removeEntity: async (entityId: string) => {
    set({ error: null });
    try {
      const response = await fetch(`api/ha/config/entity/${encodeURIComponent(entityId)}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to remove entity: ${response.statusText}`);
      }
      
      // Update local state
      set((prev) => {
        const { [entityId]: removed, ...remainingStates } = prev.entityStates;
        return {
          entities: prev.entities.filter(e => e.entity_id !== entityId),
          entityStates: remainingStates
        };
      });
    } catch (error) {
      console.error(`Error removing entity ${entityId}:`, error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to remove entity'
      });
    }
  },

  // Update entity state (for WebSocket updates)
  updateEntityState: (entityId: string, state: EntityState) => {
    set((prev) => ({
      entityStates: {
        ...prev.entityStates,
        [entityId]: state
      }
    }));
  },

  // Set error message
  setError: (error: string | null) => {
    set({ error });
  }
}));

// Export a convenience function to match the previous API
export const useHAStore = haStore;
