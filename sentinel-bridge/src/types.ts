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
  | { cmd: "quit" }
  | { cmd: "map_state" }
  | { cmd: "map_region"; region_id: string }
  // Turn-based travel commands (Sentinel 2D Phase 7)
  | { cmd: "travel_propose"; region_id: string; via?: string }
  | { cmd: "travel_commit"; via?: string }
  | { cmd: "travel_cancel" };

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

// ─── Map Types (Sentinel 2D) ──────────────────────────────────────────────────

export type RegionConnectivity =
  | "disconnected"
  | "aware"
  | "connected"
  | "embedded";

export type Region =
  | "frozen_edge"
  | "pacific_corridor"
  | "northern_reaches"
  | "rust_corridor"
  | "breadbasket"
  | "northeast_scar"
  | "desert_sprawl"
  | "appalachian_hollows"
  | "texas_spine"
  | "gulf_passage"
  | "sovereign_south";

export interface ContentMarker {
  type: "current" | "job" | "thread" | "npc" | "locked" | "risky";
  count?: number;
}
export interface RegionMapState {
  connectivity: RegionConnectivity;
  markers: ContentMarker[];
}

export interface MapState {
  ok: boolean;
  current_region: Region;
  regions: Record<string, RegionMapState>;
}

export interface RouteRequirementResult {
  type: string;
  faction?: string;
  min_standing?: string;
  vehicle_capability?: string;
  met: boolean;
}

export interface RouteAlternativeResult {
  type: string;
  description: string;
  cost?: Record<string, number>;
  consequence?: string;
  available: boolean;
}

export interface RouteFromCurrent {
  from: Region;
  to: Region;
  requirements: RouteRequirementResult[];
  alternatives: RouteAlternativeResult[];
  traversable: boolean;
  best_option: "direct" | "alternative" | "blocked";
}

export interface RegionDetail {
  ok: boolean;
  region: {
    id: Region;
    name: string;
    description: string;
    primary_faction: string;
    contested_by: string[];
    terrain: string[];
    character: string;
    connectivity: RegionConnectivity;
    position: { x: number; y: number };
  };
  routes_from_current: RouteFromCurrent[];
  content: {
    npcs: string[];
    jobs: string[];
    threads: string[];
  };
}

export type MapEventType =
  | "map.region_changed"
  | "map.connectivity_updated"
  | "map.marker_changed"
  | "map.route_status_changed";

// ─── Turn-Based Travel Types (Sentinel 2D Phase 7) ─────────────────────────

export type RequirementStatus = "met" | "unmet" | "bypassable";

export interface TravelRequirement {
  label: string;
  status: RequirementStatus;
  detail: string;
  bypass: string | null;
}

export interface TravelCostPreview {
  turns: number;
  social_energy: number;
  credits: number;
  fuel: number;
  condition: number;
  standing_changes: Record<string, number>;
}

export interface TravelRisk {
  label: string;
  severity: "low" | "medium" | "high";
  detail: string;
}

export interface TravelAlternative {
  label: string;
  type: string;
  description: string;
  consequence: string | null;
  costs: {
    turns: number;
    social_energy: number;
    credits: number;
  };
}

export interface TravelProposal {
  action_type: "travel";
  region_id: Region;
  state_version: number;
  feasible: boolean;
  summary: string;
  requirements: TravelRequirement[];
  costs: TravelCostPreview;
  risks: TravelRisk[];
  alternatives: TravelAlternative[];
}

export interface TravelProposalResponse {
  ok: true;
  proposal: TravelProposal;
}

export interface TurnEventResult {
  event_id: string;
  event_type: string;
  summary: string;
  cascade_depth: number;
  payload: Record<string, unknown>;
}

export interface CascadeNotice {
  headline: string;
  details: string[];
  severity: "info" | "warning" | "critical";
}

export interface TurnResult {
  action_id: string;
  success: boolean;
  state_version: number;
  turn_number: number;
  events: TurnEventResult[];
  cascade_notices: CascadeNotice[];
  narrative_hooks: string[];
  state_snapshot: Record<string, unknown>;
}

export interface TravelCommitResponse {
  ok: true;
  turn_result: TurnResult;
}
