export const WEEKDAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

/**
 * Get human-readable time ago string
 */
export function getTimeAgo(timestamp: number): string {
  const now = Date.now() / 1000; // Convert to seconds
  const diff = now - timestamp;

  if (diff < 5) return "just now";
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/**
 * Get weekday name from number (0=Sunday, 1=Monday, etc.)
 */
export function getWeekdayName(weekday: number): string {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return days[weekday] || 'Unknown';
}

/**
 * Format time and weekday into a readable format like "2:42 PM Wednesday"
 */
export function formatDateTime(hour: number, minute: number, weekday: number): string {
  // Convert 24-hour to 12-hour format
  const hour12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const timeStr = `${hour12}:${String(minute).padStart(2, '0')} ${ampm}`;

  const weekdayName = getWeekdayName(weekday);
  return `${timeStr} ${weekdayName}`;
}

/**
 * Format datetime string for display
 */
export function formatDateTimeString(isoString: string | undefined): string {
  if (!isoString) return 'Never';

  try {
    const date = new Date(isoString);
    return date.toLocaleString();
  } catch {
    return 'Invalid date';
  }
}

export function escapeHtml(value: string): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function pad2(value: number | null | undefined): string {
  if (!Number.isFinite(value ?? Number.NaN)) {
    return "00";
  }
  const normalized = Math.max(0, Math.min(99, Math.floor(value ?? 0)));
  return normalized.toString().padStart(2, "0");
}

export function formatRawPayload(hex: string): string {
  const cleaned = hex.replace(/\s+/g, "");
  const bytes: string[] = [];
  for (let i = 0; i < cleaned.length; i += 2) {
    const part = cleaned.substring(i, i + 2);
    if (part.length === 2) {
      bytes.push(part.toUpperCase());
    }
  }
  return bytes.join(" ");
}

export function formatTimestamp(timestamp: number): string {
  if (!Number.isFinite(timestamp)) {
    return "Unknown";
  }
  const date = new Date(timestamp * 1000);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return `${date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  })} ${date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })}`;
}

export function formatDayTime(
  weekday: number | null,
  hour: number | null,
  minute: number | null
): string {
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    return "";
  }
  const time = `${pad2(hour)}:${pad2(minute)}`;
  if (Number.isFinite(weekday) && weekday !== null) {
    const index = Math.max(0, Math.min(WEEKDAY_NAMES.length - 1, Math.floor(weekday)));
    return `${WEEKDAY_NAMES[index]} ${time}`;
  }
  return time;
}

export function renderNotice(
  message: string,
  variant: "info" | "success" | "warning" | "error" = "info",
  escape = escapeHtml
): string {
  const role = variant === "error" ? "alert" : "status";
  const classes = ["notice", variant !== "info" ? variant : ""].filter(Boolean).join(" ");
  return `<div class="${classes}" role="${role}">${escape(message)}</div>`;
}

export function renderParsedRaw(parsed: Record<string, unknown> | null): string {
  if (!parsed) {
    return "<em>No decoded payload</em>";
  }
  try {
    const json = JSON.stringify(parsed, null, 2);
    return `<pre class="code-block">${escapeHtml(json)}</pre>`;
  } catch {
    return "<em>Unable to render decoded payload</em>";
  }
}

/**
 * Get the configured name for a device, falling back to model name
 * Note: This function requires dashboard state access
 */
export function getDeviceDisplayName(deviceAddress: string, getDashboardState: () => any): string {
  const state = getDashboardState();
  const device = state.deviceStatus?.[deviceAddress];

  if (!device) return 'Unknown Device';

  // First, check if there's a configured name in metadata
  if (device.device_type === "doser") {
    const metadata = state.doserMetadata.find((m: any) => m.id === deviceAddress);
    if (metadata?.name) return metadata.name;
  } else if (device.device_type === "light") {
    const metadata = state.lightMetadata.find((m: any) => m.id === deviceAddress);
    if (metadata?.name) return metadata.name;
  }

  // Fall back to model name or generic name
  return device.model_name || "Unknown Device";
}

/**
 * Get channel names for a device based on its model
 * Note: This function requires dashboard state access
 */
export function getDeviceChannelNames(deviceAddress: string, getDashboardState: () => any): string[] {
  const state = getDashboardState();
  const device = state.deviceStatus?.[deviceAddress];

  if (!device) return ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'];

  const modelName = device.model_name?.toLowerCase() || '';

  // WRGB devices have Red, Green, Blue, White channels
  if (modelName.includes('wrgb')) {
    return ['Red', 'Green', 'Blue', 'White'];
  }

  // RGB devices
  if (modelName.includes('rgb')) {
    return ['Red', 'Green', 'Blue', 'Channel 4'];
  }

  // Default fallback
  return ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'];
}
