import { css } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

export const cardStyles = css`
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

  .section {
    margin-bottom: 20px;
  }

  .section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary-text-color);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  /* Timeline & Curve Visualiser */
  .timeline-container {
    background: var(--card-background-color, #1e1e1e);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    border: 1px solid var(--divider-color, #333);
  }

  .curve-svg {
    width: 100%;
    height: 140px;
    overflow: visible;
  }

  .timeline-axis text {
    fill: var(--secondary-text-color, #888);
    font-size: 10px;
  }

  .timeline-grid line {
    stroke: var(--divider-color, rgba(255, 255, 255, 0.1));
    stroke-dasharray: 2 2;
  }

  .time-marker-line {
    stroke: var(--accent-color, #ff9800);
    stroke-width: 1.5;
    stroke-dasharray: 3 3;
  }

  /* Schedule Cards */
  .schedule-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 16px;
  }

  .schedule-item {
    background: var(--secondary-background-color, rgba(255, 255, 255, 0.04));
    border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .schedule-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
  }

  .schedule-times {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .schedule-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
  }

  .channel-pills {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 4px;
  }

  .channel-pill {
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .channel-pill.red { background: rgba(244, 67, 54, 0.2); color: #f44336; }
  .channel-pill.green { background: rgba(76, 175, 80, 0.2); color: #4caf50; }
  .channel-pill.blue { background: rgba(33, 150, 243, 0.2); color: #2196f3; }
  .channel-pill.white { background: rgba(255, 255, 255, 0.2); color: var(--primary-text-color); }

  /* Form Elements */
  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  .time-input-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .time-input-group label {
    font-size: 0.8rem;
    color: var(--secondary-text-color);
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

  .slider-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .slider-label {
    width: 60px;
    font-size: 0.85rem;
    font-weight: 500;
  }

  .slider-row ha-slider {
    flex: 1;
  }

  .slider-val {
    width: 36px;
    text-align: right;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
  }

  /* Weekday Selector */
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
    transition: all 0.2s ease;
  }

  .weekday-btn.selected {
    background: var(--primary-color);
    color: var(--primary-text-color, #fff);
    border-color: var(--primary-color);
  }

  /* Action Buttons */
  .button-row {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 16px;
  }

  mwc-button, ha-button {
    cursor: pointer;
  }

  .danger-btn {
    --mdc-theme-primary: var(--error-color, #f44336);
  }

  .empty-state {
    text-align: center;
    padding: 24px 12px;
    color: var(--secondary-text-color);
    font-size: 0.9rem;
  }
`;
