/**
 * Shared types for the Sentinel bridge.
 *
 * These mirror the headless.py JSON contract.
 */

// Commands that can be sent to Sentinel
export type SentinelCommand =
  | { cmd: "status" }
  | { cmd: "say"; text: string }
  | { cmd: "slash"; command: string; args?: string[] }
  | { cmd: "load"; campaign_id: string }
  | { cmd: "save" }
  | { cmd: "quit" };

// Response from Sentinel
export interface SentinelResponse {
  type: "ready" | "result" | "event" | "error";
  ok?: boolean;
  error?: string;
  [key: string]: unknown;
}

// Game event emitted by Sentinel
export interface GameEvent {
  type: "event";
  event_type: string;
  data: Record<string, unknown>;
  campaign_id: string | null;
  session: number | null;
  timestamp: string;
}

// Status response
export interface StatusResponse {
  ok: boolean;
  backend: string;
  campaign: {
    id: string | null;
    name: string | null;
    session: number;
  } | null;
  conversation_length: number;
}

// Bridge state
export type ProcessState = "stopped" | "starting" | "ready" | "error";

export interface BridgeStatus {
  state: ProcessState;
  sentinel: StatusResponse | null;
  error: string | null;
  restartCount: number;
  uptime: number | null;
}
