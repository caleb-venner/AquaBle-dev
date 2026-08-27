/**
 * AquaBle Light Schedule & Control Card
 *
 * A Lovelace card for managing auto-schedules, 24h ramp curves, and manual
 * brightness for Chihiros LED lights via AquaBle.
 */

import { LitElement } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";
import { DOMAIN, SERVICES } from "./constants.js";
import { cardStyles } from "./light-card-styles.js";
import { renderCard } from "./light-card-render.js";

class AquaBleLightCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
      _activeTab: { type: String },
      _loading: { type: Boolean },
      _newSchedule: { type: Object },
      _manualLevels: { type: Object },
    };
  }

  constructor() {
    super();
    this._activeTab = "schedules";
    this._loading = false;
    this._newSchedule = {
      sunriseHour: 8,
      sunriseMinute: 0,
      sunsetHour: 18,
      sunsetMinute: 0,
      rampMinutes: 30,
      weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
      channels: [50, 50, 50, 50],
    };
    this._manualLevels = [0, 0, 0, 0];
  }

  setConfig(config) {
    this._config = { ...config };
  }

  static get styles() {
    return cardStyles;
  }

  render() {
    return renderCard(this);
  }

  // --- Entity & Device Resolution ---

  get _activeSchedulesEntity() {
    if (!this.hass) return null;
    if (this._config && this._config.entity) {
      return this.hass.states[this._config.entity] || null;
    }
    // Auto-discover active schedules sensor
    const entityId = Object.keys(this.hass.states).find(
      (id) => id.startsWith("sensor.") && id.includes("active_schedules")
    );
    return entityId ? this.hass.states[entityId] : null;
  }

  get _syncState() {
    if (!this.hass) return null;
    const activeEntity = this._activeSchedulesEntity;
    if (activeEntity) {
      const syncEntityId = activeEntity.entity_id.replace("active_schedules", "hardware_sync");
      if (this.hass.states[syncEntityId]) {
        return this.hass.states[syncEntityId];
      }
    }
    const fallbackId = Object.keys(this.hass.states).find(
      (id) => id.startsWith("sensor.") && id.includes("hardware_sync")
    );
    return fallbackId ? this.hass.states[fallbackId] : null;
  }

  get _deviceName() {
    const active = this._activeSchedulesEntity;
    if (active && active.attributes && active.attributes.friendly_name) {
      return active.attributes.friendly_name.replace(" Active Schedules", "");
    }
    return "AquaBle Light";
  }

  get _schedules() {
    const active = this._activeSchedulesEntity;
    if (active && active.attributes && Array.isArray(active.attributes.schedules)) {
      return active.attributes.schedules;
    }
    return [];
  }

  get _deviceId() {
    if (this._config && this._config.device_id) {
      return this._config.device_id;
    }
    // Find device ID via entity registry / hass devices if available
    const active = this._activeSchedulesEntity;
    return active ? (active.attributes.device_id || active.entity_id) : "";
  }

  // --- UI Event Handlers ---

  _setTab(tab) {
    this._activeTab = tab;
  }

  _updateNewSchedule(key, value) {
    this._newSchedule = {
      ...this._newSchedule,
      [key]: value,
    };
  }

  _updateChannelLevel(index, value) {
    const updated = [...this._newSchedule.channels];
    updated[index] = value;
    this._newSchedule = {
      ...this._newSchedule,
      channels: updated,
    };
  }

  _toggleWeekday(key) {
    const current = this._newSchedule.weekdays;
    let next;
    if (current.includes(key)) {
      next = current.filter((d) => d !== key);
    } else {
      next = [...current, key];
    }
    this._newSchedule = {
      ...this._newSchedule,
      weekdays: next,
    };
  }

  _updateManualLevel(index, value) {
    const updated = [...this._manualLevels];
    updated[index] = value;
    this._manualLevels = updated;
  }

  // --- Service Actions ---

  async _saveSchedule() {
    if (!this.hass) return;
    this._loading = true;
    try {
      const active = this._activeSchedulesEntity;
      const deviceId = this._config?.device_id || active?.entity_id;

      await this.hass.callService(DOMAIN, SERVICES.SET_LIGHT_AUTO, {
        device_id: deviceId,
        sunrise_hour: this._newSchedule.sunriseHour,
        sunrise_minute: this._newSchedule.sunriseMinute,
        sunset_hour: this._newSchedule.sunsetHour,
        sunset_minute: this._newSchedule.sunsetMinute,
        ramp_up_minutes: this._newSchedule.rampMinutes,
        red: this._newSchedule.channels[0],
        green: this._newSchedule.channels[1],
        blue: this._newSchedule.channels[2],
        white: this._newSchedule.channels[3],
        weekdays: this._newSchedule.weekdays,
      });
      this._activeTab = "schedules";
    } catch (err) {
      console.error("Failed to push auto schedule:", err);
    } finally {
      this._loading = false;
    }
  }

  async _clearSchedules() {
    if (!this.hass) return;
    if (!confirm("Are you sure you want to clear all auto-schedules from this light?")) {
      return;
    }
    this._loading = true;
    try {
      const active = this._activeSchedulesEntity;
      const deviceId = this._config?.device_id || active?.entity_id;

      await this.hass.callService(DOMAIN, SERVICES.CLEAR_LIGHT_SCHEDULES, {
        device_id: deviceId,
      });
    } catch (err) {
      console.error("Failed to clear schedules:", err);
    } finally {
      this._loading = false;
    }
  }

  async _setLightMode(mode) {
    if (!this.hass) return;
    this._loading = true;
    try {
      const active = this._activeSchedulesEntity;
      const deviceId = this._config?.device_id || active?.entity_id;

      await this.hass.callService(DOMAIN, SERVICES.ENABLE_LIGHT_AUTO, {
        device_id: deviceId,
        mode: mode,
      });
    } catch (err) {
      console.error("Failed to set light mode:", err);
    } finally {
      this._loading = false;
    }
  }

  async _applyManualBrightness() {
    if (!this.hass) return;
    this._loading = true;
    try {
      const active = this._activeSchedulesEntity;
      const deviceId = this._config?.device_id || active?.entity_id;

      await this.hass.callService(DOMAIN, SERVICES.SET_LIGHT_MANUAL, {
        device_id: deviceId,
        red: this._manualLevels[0],
        green: this._manualLevels[1],
        blue: this._manualLevels[2],
        white: this._manualLevels[3],
      });
    } catch (err) {
      console.error("Failed to set manual brightness:", err);
    } finally {
      this._loading = false;
    }
  }
}

if (!customElements.get("aquable-light-card")) {
  customElements.define("aquable-light-card", AquaBleLightCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "aquable-light-card")) {
  window.customCards.push({
    type: "aquable-light-card",
    name: "AquaBle Light Schedule Card",
    description: "Visualise 24h ramp curves and configure auto-schedules for Chihiros LED lights.",
  });
}
