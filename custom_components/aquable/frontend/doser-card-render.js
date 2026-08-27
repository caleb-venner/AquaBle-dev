import { html } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";
import { WEEKDAYS } from "./constants.js";

export function renderDoserCard(card) {
  const syncStatus = card._syncStatus;
  const deviceName = card._deviceName;

  return html`
    <ha-card>
      <div class="card-header">
        <div class="card-title">
          <ha-icon icon="mdi:water-pump"></ha-icon>
          <span>${deviceName || "Chihiros Dosing Pump"}</span>
        </div>
        <div class="sync-badge ${syncStatus === 'synced' ? 'synced' : 'unavailable'}">
          ${syncStatus === "synced" ? "Online" : "Offline"}
        </div>
      </div>

      <div class="tabs">
        <div
          class="tab ${card._activeTab === 'heads' ? 'active' : ''}"
          @click=${() => card._setTab('heads')}
        >
          Pump Heads
        </div>
        <div
          class="tab ${card._activeTab === 'configure' ? 'active' : ''}"
          @click=${() => card._setTab('configure')}
        >
          Configure Schedules
        </div>
      </div>

      ${card._activeTab === 'heads' ? renderHeadsTab(card) : ''}
      ${card._activeTab === 'configure' ? renderConfigureTab(card) : ''}
    </ha-card>
  `;
}

function renderHeadsTab(card) {
  const heads = card._headsData;

  return html`
    <div class="heads-grid">
      ${heads.map((head) => {
        const percent = head.targetDose > 0
          ? Math.min(100, Math.round((head.dosedToday / head.targetDose) * 100))
          : 0;
        const isDisabled = head.mode.toLowerCase() === "disabled" || head.targetDose === 0;

        return html`
          <div class="head-card ${isDisabled ? 'disabled' : ''}">
            <div class="head-header">
              <div class="head-title-group">
                <div class="head-number-badge">${head.index}</div>
                <div class="head-name">${head.name}</div>
              </div>
              <div class="head-status-toggle">
                <ha-switch
                  .checked=${!isDisabled}
                  @change=${(e) => card._toggleHeadActive(head.index, e.target.checked)}
                  ?disabled=${card._loading}
                ></ha-switch>
              </div>
            </div>

            <!-- Progress Bar -->
            <div class="progress-section">
              <div class="progress-labels">
                <span>Dosed Today</span>
                <span class="progress-amount">
                  ${head.dosedToday.toFixed(1)} / ${head.targetDose.toFixed(1)} mL (${percent}%)
                </span>
              </div>
              <div class="progress-bar-bg">
                <div
                  class="progress-bar-fill ${percent >= 100 ? 'complete' : ''}"
                  style="width: ${percent}%;"
                ></div>
              </div>
            </div>

            <!-- Meta details -->
            <div class="head-meta-row">
              <div class="meta-pill">
                <ha-icon icon="mdi:clock-outline" style="--mdc-icon-size: 16px;"></ha-icon>
                <span>${head.scheduleTime || "--:--"}</span>
              </div>
              <div class="meta-pill">
                <ha-icon icon="mdi:cog" style="--mdc-icon-size: 16px;"></ha-icon>
                <span>${head.mode || "Daily"}</span>
              </div>
              <div class="meta-pill">
                <ha-icon icon="mdi:chart-timeline-variant-shimmer" style="--mdc-icon-size: 16px;"></ha-icon>
                <span>${head.lifetimeTotal ? `${head.lifetimeTotal.toFixed(1)} mL` : "Total"}</span>
              </div>
            </div>

            <!-- Manual Dose Trigger -->
            <div class="manual-dose-row">
              <button
                class="quick-dose-btn"
                @click=${() => card._manualDose(head.index, 1.0)}
                ?disabled=${card._loading}
              >
                +1.0 mL
              </button>
              <button
                class="quick-dose-btn"
                @click=${() => card._manualDose(head.index, 5.0)}
                ?disabled=${card._loading}
              >
                +5.0 mL
              </button>
              <input
                type="number"
                class="custom-dose-input"
                min="0.1"
                step="0.5"
                placeholder="mL"
                .value=${card._manualDoseAmounts[head.index] || ""}
                @change=${(e) => card._setCustomDoseAmount(head.index, parseFloat(e.target.value))}
              />
              <mwc-button
                dense
                unelevated
                @click=${() => card._triggerCustomDose(head.index)}
                ?disabled=${card._loading || !card._manualDoseAmounts[head.index]}
              >
                Dose
              </mwc-button>
            </div>
          </div>
        `;
      })}
    </div>
  `;
}

function renderConfigureTab(card) {
  const selectedHead = card._selectedConfigHead;
  const config = card._headConfigs[selectedHead] || {
    targetVolume: 5.0,
    hour: 8,
    minute: 0,
    weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
  };

  return html`
    <div class="section">
      <div class="section-title">
        <ha-icon icon="mdi:format-list-numbered"></ha-icon>
        Select Pump Head
      </div>
      <div class="head-select-row">
        ${[1, 2, 3, 4].map(
          (idx) => html`
            <div
              class="head-tab-btn ${selectedHead === idx ? 'selected' : ''}"
              @click=${() => card._selectConfigHead(idx)}
            >
              Head ${idx}
            </div>
          `
        )}
      </div>

      <div class="form-grid">
        <div class="input-group">
          <label>Daily Target Dose (mL)</label>
          <input
            type="number"
            min="0"
            max="500"
            step="0.1"
            .value=${config.targetVolume}
            @change=${(e) => card._updateHeadConfig(selectedHead, 'targetVolume', parseFloat(e.target.value))}
          />
        </div>

        <div class="input-group">
          <label>Scheduled Dosing Time</label>
          <div class="time-pickers">
            <input
              type="number"
              min="0"
              max="23"
              .value=${config.hour}
              @change=${(e) => card._updateHeadConfig(selectedHead, 'hour', parseInt(e.target.value, 10))}
            />
            <span>:</span>
            <input
              type="number"
              min="0"
              max="59"
              .value=${config.minute}
              @change=${(e) => card._updateHeadConfig(selectedHead, 'minute', parseInt(e.target.value, 10))}
            />
          </div>
        </div>
      </div>

      <div class="section-title">
        <ha-icon icon="mdi:calendar-week"></ha-icon>
        Active Weekdays
      </div>
      <div class="weekday-row">
        ${WEEKDAYS.map(
          (d) => html`
            <div
              class="weekday-btn ${(config.weekdays || []).includes(d.key) ? 'selected' : ''}"
              @click=${() => card._toggleHeadWeekday(selectedHead, d.key)}
            >
              ${d.label}
            </div>
          `
        )}
      </div>

      <div class="button-row">
        <mwc-button
          raised
          @click=${() => card._saveHeadSchedule(selectedHead)}
          ?disabled=${card._loading}
        >
          <ha-icon icon="mdi:content-save-check" slot="icon"></ha-icon>
          Save Head ${selectedHead} Schedule
        </mwc-button>
      </div>
    </div>
  `;
}
