import { css } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

export const doserCardStyles = css`
  ha-card {
    padding: 16px;
    box-sizing: border-box;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .card-title {
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--primary-text-color);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .sync-badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .sync-badge.synced {
    background-color: rgba(76, 175, 80, 0.15);
    color: var(--success-color, #4caf50);
  }

  .sync-badge.unavailable {
    background-color: rgba(244, 67, 54, 0.15);
    color: var(--error-color, #f44336);
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    margin-bottom: 16px;
  }

  .tab {
    padding: 8px 16px;
    cursor: pointer;
    font-weight: 500;
    color: var(--secondary-text-color);
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
  }

  .tab.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }

  /* Head Grid (2 columns on tablet/desktop, 1 column on narrow mobile) */
  .heads-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 14px;
    margin-bottom: 16px;
  }

  .head-card {
    background: var(--secondary-background-color, rgba(255, 255, 255, 0.04));
    border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    position: relative;
    overflow: hidden;
  }

  .head-card.disabled {
    opacity: 0.75;
    border-style: dashed;
  }

  .head-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .head-title-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .head-number-badge {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--primary-color, #03a9f4);
    color: var(--primary-text-color, #fff);
    font-size: 0.8rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .head-name {
    font-size: 1rem;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .head-status-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  /* Progress Section */
  .progress-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .progress-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
  }

  .progress-amount {
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .progress-bar-bg {
    height: 10px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 5px;
    overflow: hidden;
    position: relative;
  }

  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--primary-color, #03a9f4), #00bcd4);
    border-radius: 5px;
    transition: width 0.3s ease;
  }

  .progress-bar-fill.complete {
    background: var(--success-color, #4caf50);
  }

  /* Meta Info Row */
  .head-meta-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: var(--secondary-text-color);
    padding-top: 4px;
    border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.06));
  }

  .meta-pill {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;
  }

  /* Manual Dose Actions */
  .manual-dose-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 4px;
  }

  .quick-dose-btn {
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color, #555);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .quick-dose-btn:hover {
    background: var(--primary-color);
    color: #fff;
  }

  .custom-dose-input {
    width: 44px;
    padding: 4px 6px;
    border-radius: 4px;
    border: 1px solid var(--divider-color, #555);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    text-align: center;
    font-size: 0.8rem;
  }

  /* Form & Settings Editor */
  .section {
    margin-bottom: 20px;
  }

  .section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary-text-color);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .head-select-row {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  .head-tab-btn {
    flex: 1;
    padding: 8px;
    border-radius: 6px;
    border: 1px solid var(--divider-color, #444);
    background: var(--card-background-color);
    color: var(--secondary-text-color);
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    text-align: center;
  }

  .head-tab-btn.selected {
    background: var(--primary-color);
    color: #fff;
    border-color: var(--primary-color);
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .input-group label {
    font-size: 0.8rem;
    color: var(--secondary-text-color);
  }

  .input-group input {
    padding: 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color, #ccc);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    font-size: 0.95rem;
  }

  .time-pickers {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .time-pickers input {
    width: 48px;
    padding: 6px 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color, #ccc);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    text-align: center;
    font-size: 0.95rem;
  }

  .weekday-row {
    display: flex;
    gap: 6px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .weekday-btn {
    flex: 1;
    min-width: 36px;
    padding: 6px 4px;
    border-radius: 6px;
    border: 1px solid var(--divider-color, #ccc);
    background: var(--card-background-color);
    color: var(--secondary-text-color);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
  }

  .weekday-btn.selected {
    background: var(--primary-color);
    color: #fff;
    border-color: var(--primary-color);
  }

  .button-row {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 16px;
  }
`;
