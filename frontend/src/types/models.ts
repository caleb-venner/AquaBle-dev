// Enhanced TypeScript interfaces matching backend models
// This file provides complete type definitions for the Chihiros Device Manager SPA
// 
// NOTE: This file now serves as a barrel export for backwards compatibility.
// Type definitions have been organized into:
// - backend-models.ts: Backend API types and responses
// - ui-models.ts: Frontend UI state and component types
// - type-guards.ts: Type guard functions and predicates
// - ../utils.ts: Utility functions for data transformation

// ========================================
// RE-EXPORTS FROM SPECIALIZED TYPE FILES
// ========================================

// Re-export comprehensive device structures from specific device types
export type { Weekday } from './doser'; // Use doser's Weekday as the canonical one
export * from './doser';
export type {
  ChannelDef,
  ChannelLevels,
  LightDevice,
  ManualProfile,
  CustomPoint,
  CustomProfile,
  AutoProgram,
  AutoProfile,
  Profile,
  Interp
} from './light';

// Re-export all backend API models
export type {
  CommandStatus,
  CommandRecord,
  CommandRequest,
  LightChannel,
  LightParsed,
  LightKeyframe,
  DoserHead,
  DoserParsed,
  CachedStatus,
  StatusResponse,
  LiveStatusResponse,
  ScanDevice,
  SetBrightnessArgs,
  AddAutoSettingArgs,
  SetScheduleArgs,
  DeviceStatus,
} from './backend-models';

// Re-export all UI models
export type {
  DeviceConfiguration,
  DeviceState,
  DeviceEntry,
  QueuedCommand,
  UIState,
  Notification,
  ManualBrightnessPayload,
} from './ui-models';

// Re-export all type guards and type-related utilities
export {
  isLightDevice,
  isDoserDevice,
  isLightParsed,
  isDoserParsed,
  isCommandComplete,
  isCommandSuccessful,
  getCommandStatusLabel,
} from './type-guards';

// Re-export utility functions from utils.ts
export {
  statusResponseToEntries,
  debugStatusesToEntries,
  getLifetimeTotalsInMl,
} from '../utils';
