/**
 * Schedule calculation utilities for light devices
 */

export interface AutoProgram {
  id: string;
  label: string;
  enabled: boolean;
  days: string[];
  sunrise: string;
  sunset: string;
  rampMinutes: number;
  levels: Record<string, number>;
  channels?: any[]; // Optional device channel definitions for ordering
}
