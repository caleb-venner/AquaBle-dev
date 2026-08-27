/**
 * AquaBle Dosing Pump Card
 *
 * A Lovelace card for monitoring pump heads, scheduling daily doses,
 * and triggering manual dosing on Chihiros Dosing Pumps.
 */

import { LitElement } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";
import { DOMAIN, DOSER_SERVICES, DEFAULT_HEAD_NAMES } from "./constants.js";
import { doserCardStyles } from "./doser-card-styles.js";
import { renderDoserCard } from "./doser-card-render.js";

class AquaBleDoserCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
      _activeTab: { type: String },
      _loading: { type: Boolean },
      _selectedConfigHead: { type: Number },
      _headConfigs: { type: Object },
      _manualDoseAmounts: { type: Object },
    };
  }

  constructor() {
    super();
    this._activeTab = "heads";
    this._loading = false;
    this._selectedConfigHead = 1;
    this._headConfigs = {
      1: { targetVolume: 5.0, hour: 8, minute: 0, weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] },
      2: { targetVolume: 5.0, hour: 8, minute: 15, weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] },
      3: { targetVolume: 5.0, hour: 8, minute: 30, weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] },
      4: { targetVolume: 5.0, hour: 8, minute: 45, weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] },
    };
    this._manualDoseAmounts = {};
  }

  setConfig(config) {
    this._config = { ...config };
  }

  static get styles() {
    return doserCardStyles;
  }

  render() {
    return renderDoserCard(this);
  }

  // --- Entity & State Resolution ---

  get _basePrefix() {
    if (!this.hass) return "";
    if (this._config && this._config.entity) {
      return this._config.entity.replace(/_head_\d+_.+$/, "");
    }
    // Auto-discover doser sensor prefix
    const sample = Object.keys(this.hass.states).find(
      (id) =>
        id.startsWith("sensor.") &&
        (id.includes("_head_1_dosed_today") || id.includes("_head_1_daily_total"))
    );
    if (sample) {
      return sample
        .replace("_head_1_dosed_today", "")
        .replace("_head_1_daily_total", "");
    }
    return "";
  }

  get _deviceName() {
    const prefix = this._basePrefix;
    if (prefix && this.hass) {
      const stateObj =
        this.hass.states[`${prefix}_head_1_dosed_today`] ||
        this.hass.states[`${prefix}_head_1_daily_total`];
      if (stateObj && stateObj.attributes && stateObj.attributes.friendly_name) {
        return stateObj.attributes.friendly_name.replace(
          / Head 1 (Dosed Today|Daily Total)/i,
          ""
        );
      }
    }
    return "Chihiros Dosing Pump";
  }

  get _syncStatus() {
    const prefix = this._basePrefix;
    if (!prefix || !this.hass) return "unavailable";
    const sample =
      this.hass.states[`${prefix}_head_1_dosed_today`] ||
      this.hass.states[`${prefix}_head_1_daily_total`];
    return sample && sample.state !== "unavailable" ? "synced" : "unavailable";
  }

  get _headsData() {
    const prefix = this._basePrefix;
    const heads = [];

    for (let idx = 1; idx <= 4; idx++) {
      const customNames = this._config?.head_names || {};
      const name = customNames[idx] || DEFAULT_HEAD_NAMES[idx] || `Head ${idx}`;

      let dosedToday = 0;
      let targetDose = 0;
      let scheduleTime = "--:--";
      let mode = "Daily";
      let lifetimeTotal = 0;

      if (prefix && this.hass) {
        const sDosed =
          this.hass.states[`${prefix}_head_${idx}_dosed_today`] ||
          this.hass.states[`${prefix}_head_${idx}_daily_total`];
        if (sDosed && !isNaN(parseFloat(sDosed.state))) {
          dosedToday = parseFloat(sDosed.state);
        }

        const sTarget = this.hass.states[`${prefix}_head_${idx}_target_dose`];
        if (sTarget && !isNaN(parseFloat(sTarget.state))) {
          targetDose = parseFloat(sTarget.state);
        }

        const sTime = this.hass.states[`${prefix}_head_${idx}_schedule_time`];
        if (sTime && sTime.state && sTime.state !== "unavailable") {
          scheduleTime = sTime.state;
        }

        const sMode = this.hass.states[`${prefix}_head_${idx}_mode`];
        if (sMode && sMode.state && sMode.state !== "unavailable") {
          mode = sMode.state;
        }

        const sLife = this.hass.states[`${prefix}_head_${idx}_lifetime_total`];
        if (sLife && !isNaN(parseFloat(sLife.state))) {
          lifetimeTotal = parseFloat(sLife.state);
        }
      }

      heads.push({
        index: idx,
        name,
        dosedToday,
        targetDose,
        scheduleTime,
        mode,
        lifetimeTotal,
      });
    }

    return heads;
  }

  get _deviceId() {
    if (this._config && this._config.device_id) {
      return this._config.device_id;
    }
    const prefix = this._basePrefix;
    if (prefix && this.hass) {
      const sample =
        this.hass.states[`${prefix}_head_1_dosed_today`] ||
        this.hass.states[`${prefix}_head_1_daily_total`];
      return sample ? (sample.attributes?.device_id || sample.entity_id) : "";
    }
    return "";
  }

  // --- UI Event Handlers ---

  _setTab(tab) {
    this._activeTab = tab;
  }

  _selectConfigHead(headIdx) {
    this._selectedConfigHead = headIdx;
    // Auto-populate form from live entity state if available
    const head = this._headsData.find((h) => h.index === headIdx);
    if (head && head.scheduleTime && head.scheduleTime.includes(":")) {
      const [h, m] = head.scheduleTime.split(":").map(Number);
      this._headConfigs = {
        ...this._headConfigs,
        [headIdx]: {
          ...this._headConfigs[headIdx],
          targetVolume: head.targetDose || this._headConfigs[headIdx].targetVolume,
          hour: isNaN(h) ? 8 : h,
          minute: isNaN(m) ? 0 : m,
        },
      };
    }
  }

  _updateHeadConfig(headIdx, key, value) {
    this._headConfigs = {
      ...this._headConfigs,
      [headIdx]: {
        ...this._headConfigs[headIdx],
        [key]: value,
      },
    };
  }

  _toggleHeadWeekday(headIdx, key) {
    const current = this._headConfigs[headIdx]?.weekdays || [];
    let next;
    if (current.includes(key)) {
      next = current.filter((d) => d !== key);
    } else {
      next = [...current, key];
    }
    this._updateHeadConfig(headIdx, "weekdays", next);
  }

  _setCustomDoseAmount(headIdx, amount) {
    this._manualDoseAmounts = {
      ...this._manualDoseAmounts,
      [headIdx]: amount,
    };
  }

  _triggerCustomDose(headIdx) {
    const amount = this._manualDoseAmounts[headIdx];
    if (amount && amount > 0) {
      this._manualDose(headIdx, amount);
    }
  }

  // --- Service Actions ---

  async _manualDose(headIdx, volumeMl) {
    if (!this.hass) return;
    this._loading = true;
    try {
      const deviceId = this._deviceId;
      await this.hass.callService(DOMAIN, DOSER_SERVICES.MANUAL_DOSE, {
        device_id: deviceId,
        head_index: headIdx,
        volume_ml: volumeMl,
      });
    } catch (err) {
      console.error("Failed to trigger manual dose:", err);
    } finally {
      this._loading = false;
    }
  }

  async _toggleHeadActive(headIdx, activate) {
    if (!this.hass) return;
    this._loading = true;
    try {
      const deviceId = this._deviceId;
      const head = this._headsData.find((h) => h.index === headIdx);
      const config = this._headConfigs[headIdx] || { hour: 8, minute: 0, weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] };

      const [h, m] = (head && head.scheduleTime && head.scheduleTime.includes(":"))
        ? head.scheduleTime.split(":").map(Number)
        : [config.hour, config.minute];

      // To deactivate, set target volume to 0. To activate, set to configured target volume.
      const targetVolume = activate ? (config.targetVolume || 5.0) : 0.0;

      await this.hass.callService(DOMAIN, DOSER_SERVICES.SET_SCHEDULE, {
        device_id: deviceId,
        head_index: headIdx,
        volume_ml: targetVolume,
        hour: isNaN(h) ? 8 : h,
        minute: isNaN(m) ? 0 : m,
        weekdays: config.weekdays,
      });
    } catch (err) {
      console.error("Failed to toggle head schedule:", err);
    } finally {
      this._loading = false;
    }
  }

  async _saveHeadSchedule(headIdx) {
    if (!this.hass) return;
    this._loading = true;
    try {
      const deviceId = this._deviceId;
      const config = this._headConfigs[headIdx];

      await this.hass.callService(DOMAIN, DOSER_SERVICES.SET_SCHEDULE, {
        device_id: deviceId,
        head_index: headIdx,
        volume_ml: config.targetVolume,
        hour: config.hour,
        minute: config.minute,
        weekdays: config.weekdays,
      });
      this._activeTab = "heads";
    } catch (err) {
      console.error("Failed to save doser schedule:", err);
    } finally {
      this._loading = false;
    }
  }
}

if (!customElements.get("aquable-doser-card")) {
  customElements.define("aquable-doser-card", AquaBleDoserCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "aquable-doser-card")) {
  window.customCards.push({
    type: "aquable-doser-card",
    name: "AquaBle Dosing Pump Card",
    description: "Monitor dosing head progress, configure daily schedules, and trigger manual doses.",
  });
}
