export const DOMAIN = "aquable";

export const SERVICES = {
  SET_LIGHT_MANUAL: "light_set_manual_mode",
  SET_LIGHT_AUTO: "light_set_auto_schedule",
  ENABLE_LIGHT_AUTO: "light_set_mode",
  CLEAR_LIGHT_SCHEDULES: "light_clear_schedules",
  DELETE_LIGHT_AUTO: "light_delete_auto_schedule",
};

export const WEEKDAYS = [
  { key: "monday", label: "Mon", bit: 64 },
  { key: "tuesday", label: "Tue", bit: 32 },
  { key: "wednesday", label: "Wed", bit: 16 },
  { key: "thursday", label: "Thu", bit: 8 },
  { key: "friday", label: "Fri", bit: 4 },
  { key: "saturday", label: "Sat", bit: 2 },
  { key: "sunday", label: "Sun", bit: 1 },
];

export const CHANNEL_COLORS = {
  0: { name: "Red", hex: "#f44336" },
  1: { name: "Green", hex: "#4caf50" },
  2: { name: "Blue", hex: "#2196f3" },
  3: { name: "White", hex: "#e0e0e0" },
};

export const DOSER_SERVICES = {
  SET_SCHEDULE: "doser_set_daily_dose_sequence",
  MANUAL_DOSE: "doser_manual_dose",
};

export const DEFAULT_HEAD_NAMES = {
  1: "Head 1",
  2: "Head 2",
  3: "Head 3",
  4: "Head 4",
};
