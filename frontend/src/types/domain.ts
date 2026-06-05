/**
 * Domain Model Types
 * Device-specific configuration and business logic types for Dosers and Lights
 */

// ========================================
// SHARED TYPES
// ========================================

export type Weekday = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';
export type Interp = 'step' | 'linear';
export type ModeKind = 'single' | 'every_hour' | 'custom_periods' | 'timer';

// ========================================
// DOSER DOMAIN MODELS
// ========================================

export interface DoserDevice {
  id: string;
  name?: string;
  headNames?: { [key: number]: string };
  heads: DoserHead[];
  createdAt?: string;
  updatedAt?: string;
}

export interface DoserHead {
  index: 1 | 2 | 3 | 4;
  label?: string;
  active: boolean;
  schedule: Schedule;
  recurrence: { days: Weekday[] };
  missedDoseCompensation: boolean;
  volumeTracking?: {
    enabled: boolean;
    capacityMl?: number;
    currentMl?: number;
    lowThresholdMl?: number;
    updatedAt?: string;
  };
  calibration: {
    mlPerSecond: number;
    lastCalibratedAt: string;
  };
  stats?: {
    dosesToday?: number;
    mlDispensedToday?: number;
  };
}

// Doser Schedule Types
export interface SingleSchedule {
  mode: 'single';
  dailyDoseMl: number;
  startTime: string; // HH:mm
}

export interface EveryHourSchedule {
  mode: 'every_hour';
  dailyDoseMl: number;
  startTime: string; // HH:mm
}

export interface CustomPeriod {
  startTime: string; // HH:mm
  endTime: string; // HH:mm
  doses: number;
}

export interface CustomPeriodsSchedule {
  mode: 'custom_periods';
  dailyDoseMl: number;
  periods: CustomPeriod[];
}

export interface TimerDose {
  time: string; // HH:mm
  quantityMl: number;
}

export interface TimerSchedule {
  mode: 'timer';
  doses: TimerDose[];
  defaultDoseQuantityMl?: number;
  dailyDoseMl?: number;
}

export type Schedule = SingleSchedule | EveryHourSchedule | CustomPeriodsSchedule | TimerSchedule;

// ========================================
// LIGHT DOMAIN MODELS
// ========================================

export interface ChannelDef {
  key: string;
  label?: string;
  min?: number; // default 0
  max?: number; // default 100
  step?: number; // default 1
}

export type ChannelLevels = Record<string, number>;

export interface LightDevice {
  id: string;
  name?: string;
  channels: ChannelDef[];
  profile: Profile;
  createdAt?: string;
  updatedAt?: string;
}

// Light Profile Types
export interface ManualProfile {
  mode: 'manual';
  levels: ChannelLevels;
}

export interface CustomPoint {
  time: string; // HH:mm
  levels: ChannelLevels;
}

export interface CustomProfile {
  mode: 'custom';
  interpolation: Interp;
  points: CustomPoint[];
}

export interface AutoProgram {
  id: string;
  label?: string;
  enabled: boolean;
  days: Weekday[];
  sunrise: string; // HH:mm
  sunset: string; // HH:mm
  rampMinutes: number;
  levels: ChannelLevels;
}

export interface AutoProfile {
  mode: 'auto';
  programs: AutoProgram[];
}

export type Profile = ManualProfile | CustomProfile | AutoProfile;
