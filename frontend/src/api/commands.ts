// Command system API functions

import { postJson, fetchJson } from "./http";
import type {
  CommandRecord,
  CommandRequest,
} from "../types/api";

/**
 * Execute a command on a device using the unified command system
 */
export async function executeCommand(
  address: string,
  request: CommandRequest
): Promise<CommandRecord> {
  return postJson<CommandRecord>(`api/devices/${encodeURIComponent(address)}/commands`, request);
}

/**
 * Get command history for a device
 */
export async function getCommandHistory(
  address: string,
  limit = 20
): Promise<CommandRecord[]> {
  return fetchJson<CommandRecord[]>(
    `api/devices/${encodeURIComponent(address)}/commands?limit=${limit}`
  );
}

/**
 * Get a specific command by ID
 */
export async function getCommand(
  address: string,
  commandId: string
): Promise<CommandRecord> {
  return fetchJson<CommandRecord>(
    `api/devices/${encodeURIComponent(address)}/commands/${encodeURIComponent(commandId)}`
  );
}
