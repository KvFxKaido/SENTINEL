/**
 * Bridge API client for communicating with the Deno bridge.
 *
 * In development: proxied through /api
 * In production: configure BRIDGE_URL
 */

const BRIDGE_URL = import.meta.env.PUBLIC_BRIDGE_URL || '/api';

export interface BridgeState {
  state: 'stopped' | 'starting' | 'ready' | 'error';
  sentinel: {
    ok: boolean;
    backend: {
      available: boolean;
      backend: string;
      model: string;
      supports_tools: boolean;
    } | null | undefined;
    campaign: {
      id: string;
      name: string;
      session: number;
    } | null;
    conversation_length: number;
  } | null;
  error: string | null;
  restartCount: number;
  uptime: number | null;
}

export type CommandResult =
  | {
      ok: true;
      response?: string;
      result?: string;
      output?: string;
      campaign?: {
        id: string;
        name: string;
        session: number;
      };
      backend?: {
        available: boolean;
        backend: string;
        model: string;
        supports_tools: boolean;
      };
      [key: string]: unknown;
    }
  | {
      ok: false;
      error: string;
    };

export interface GearItem {
  id: string;
  name: string;
  category: string;
  used: boolean;
}

export interface Enhancement {
  id: string;
  name: string;
  source: string;
  benefit: string;
}

export interface Vehicle {
  id: string;
  name: string;
  type: string;
  description?: string;
  fuel: number;
  condition: number;
  status: 'Operational' | 'Low Fuel' | 'Needs Repair' | 'Out of Fuel' | 'Broken Down';
  terrain: string[];
  capacity: number;
  cargo: boolean;
  stealth: boolean;
}

export interface NpcSummary {
  id: string;
  name: string;
  faction: string | null;
  disposition: string;
  base_disposition: string;
  personal_standing: number;
  status: "active" | "dormant";
  last_interaction: string;
}

export type CampaignState =
  | {
      ok: true;
      campaign: {
        id: string;
        name: string;
        session: number;
        phase: number;
      };
      character: {
        name: string | null;
        background: string | null;
        social_energy: {
          current: number;
          max: number;
        };
        credits: number;
        gear: GearItem[];
        enhancements: Enhancement[];
      } | null;
      region: string | null;
      location: string | null;
      session_phase: string | null;
      loadout: string[] | null;
      factions: Array<{
        id: string;
        name: string;
        standing: string;
      }>;
      npcs: NpcSummary[];
      threads: Array<{
        id: string;
        origin: string;
        trigger: string;
        consequence: string;
        severity: string;
        created_session: number;
      }>;
      active_jobs: number;
      dormant_threads: number;
      vehicles: Vehicle[];
    }
  | {
      ok: false;
      error: string;
    };

export interface GameEvent {
  type: 'event';
  event_type: string;
  data: Record<string, unknown>;
  campaign_id: string | null;
  session: number | null;
  timestamp: string;
}

/**
 * Get current bridge and Sentinel state.
 */
export async function getState(): Promise<BridgeState> {
  const response = await fetch(`${BRIDGE_URL}/state`);
  if (!response.ok) {
    throw new Error(`Failed to get state: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Check if bridge is healthy.
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BRIDGE_URL}/health`);
    const data = await response.json();
    return data.ok === true;
  } catch {
    return false;
  }
}

/**
 * Send a command to Sentinel.
 */
export async function sendCommand(
  cmd: string,
  params: Record<string, unknown> = {}
): Promise<CommandResult> {
  const response = await fetch(`${BRIDGE_URL}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd, ...params }),
  });

  if (!response.ok) {
    throw new Error(`Command failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send player text to the GM.
 */
export async function say(text: string): Promise<CommandResult> {
  return sendCommand('say', { text });
}

/**
 * Execute a slash command.
 */
export async function slash(command: string, args: string[] = []): Promise<CommandResult> {
  return sendCommand('slash', { command, args });
}

/**
 * Get current status.
 */
export async function status(): Promise<CommandResult> {
  return sendCommand('status');
}

/**
 * Get detailed campaign state for UI rendering.
 */
export async function getCampaignState(): Promise<CampaignState> {
  const response = await fetch(`${BRIDGE_URL}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd: 'campaign_state' }),
  });

  if (!response.ok) {
    return { ok: false, error: `Request failed: ${response.statusText}` };
  }

  return response.json();
}

/**
 * Load a campaign.
 */
export async function loadCampaign(campaignId: string): Promise<CommandResult> {
  return sendCommand('load', { campaign_id: campaignId });
}

/**
 * Save current campaign.
 */
export async function saveCampaign(): Promise<CommandResult> {
  return sendCommand('save');
}

/**
 * Subscribe to SSE events from the bridge.
 * Returns a cleanup function to close the connection.
 */
export function subscribeToEvents(
  onEvent: (event: GameEvent) => void,
  onError?: (error: Event) => void
): () => void {
  const eventSource = new EventSource(`${BRIDGE_URL}/events`);

  eventSource.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as GameEvent;
      onEvent(event);
    } catch (err) {
      console.error('Failed to parse event:', err);
    }
  };

  eventSource.onerror = (e) => {
    if (onError) {
      onError(e);
    } else {
      console.error('EventSource error:', e);
    }
  };

  return () => {
    eventSource.close();
  };
}

// ─── Map API (Sentinel 2D) ────────────────────────────────────────────────────

export interface MapRegionState {
  connectivity: 'disconnected' | 'aware' | 'connected' | 'embedded';
  markers: Array<{
    type: 'current' | 'job' | 'thread' | 'npc' | 'locked' | 'risky';
    count?: number;
  }>;
}

export interface MapState {
  ok: true;
  current_region: string;
  regions: Record<string, MapRegionState>;
}

export interface RegionDetailResponse {
  ok: true;
  region: {
    id: string;
    name: string;
    description: string;
    primary_faction: string;
    contested_by: string[];
    terrain: string[];
    character: string;
    connectivity: 'disconnected' | 'aware' | 'connected' | 'embedded';
    position: { x: number; y: number };
  };
  routes_from_current: Array<{
    from: string;
    to: string;
    requirements: Array<{
      type: string;
      faction?: string;
      min_standing?: string;
      vehicle_capability?: string;
      met: boolean;
    }>;
    alternatives: Array<{
      type: string;
      description: string;
      cost?: Record<string, number>;
      consequence?: string;
      available: boolean;
    }>;
    traversable: boolean;
    best_option: 'direct' | 'alternative' | 'blocked';
  }>;
  content: {
    npcs: string[];
    jobs: string[];
    threads: string[];
  };
}

export type MapEvent = {
  type: 'event';
  event_type:
    | 'map.region_changed'
    | 'map.connectivity_updated'
    | 'map.marker_changed'
    | 'map.route_status_changed';
  data: Record<string, unknown>;
  campaign_id: string | null;
  session: number | null;
  timestamp: string;
};

/**
 * Get complete map state with all regions and content markers.
 */
export async function getMapState(): Promise<MapState> {
  const response = await fetch(`${BRIDGE_URL}/map`);
  if (!response.ok) {
    throw new Error(`Failed to get map state: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get detailed info for a specific region, including route feasibility.
 */
export async function getRegionDetail(regionId: string): Promise<RegionDetailResponse> {
  const response = await fetch(`${BRIDGE_URL}/map/region/${encodeURIComponent(regionId)}`);
  if (!response.ok) {
    throw new Error(`Failed to get region detail: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Initiate travel to a region (via the existing command interface).
 * This passes through the commitment gate — the engine validates and resolves.
 * @deprecated Use proposeTravel() + commitTravel() for turn-based travel
 */
export async function travel(regionId: string, via?: string): Promise<CommandResult> {
  const args = [regionId];
  if (via) {
    args.push('--via', via);
  }
  return sendCommand('slash', { command: 'travel', args });
}

// ─── Turn-Based Travel (Sentinel 2D Phase 7) ──────────────────────────────

export interface TravelProposal {
  action_type: 'travel';
  region_id: string;
  state_version: number;
  feasible: boolean;
  summary: string;
  requirements: Array<{
    label: string;
    status: 'met' | 'unmet' | 'bypassable';
    detail: string;
    bypass: string | null;
  }>;
  costs: {
    turns: number;
    social_energy: number;
    credits: number;
    fuel: number;
    condition: number;
    standing_changes: Record<string, number>;
  };
  risks: Array<{
    label: string;
    severity: 'low' | 'medium' | 'high';
    detail: string;
  }>;
  alternatives: Array<{
    label: string;
    type: string;
    description: string;
    consequence: string | null;
    costs: { turns: number; social_energy: number; credits: number };
  }>;
}

export interface TravelProposalResponse {
  ok: true;
  proposal: TravelProposal;
}

export interface TurnEventSummary {
  event_id: string;
  event_type: string;
  summary: string;
  cascade_depth: number;
  payload: Record<string, unknown>;
}

export interface CascadeNotice {
  headline: string;
  details: string[];
  severity: 'info' | 'warning' | 'critical';
}

export interface TurnResult {
  action_id: string;
  success: boolean;
  state_version: number;
  turn_number: number;
  events: TurnEventSummary[];
  cascade_notices: CascadeNotice[];
  narrative_hooks: string[];
  state_snapshot: Record<string, unknown>;
}

export interface TravelCommitResponse {
  ok: true;
  turn_result: TurnResult;
}

/**
 * Propose travel to a region — returns costs, requirements, and alternatives.
 * No state mutation occurs. Cancel at any point with cancelTravel().
 */
export async function proposeTravel(
  regionId: string,
): Promise<TravelProposalResponse | { ok: false; error: string }> {
  const response = await fetch(`${BRIDGE_URL}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd: 'travel_propose', region_id: regionId }),
  });
  return response.json();
}

/**
 * Commit the proposed travel — this is the commitment gate.
 * Resolves deterministically and returns a TurnResult with events and state.
 */
export async function commitTravel(
  via?: string,
): Promise<TravelCommitResponse | { ok: false; error: string }> {
  const response = await fetch(`${BRIDGE_URL}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd: 'travel_commit', via }),
  });
  return response.json();
}

/**
 * Cancel the pending travel proposal — zero side effects.
 */
export async function cancelTravel(): Promise<{ ok: boolean; message?: string; error?: string }> {
  const response = await fetch(`${BRIDGE_URL}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd: 'travel_cancel' }),
  });
  return response.json();
}

/**
 * Subscribe to map-specific SSE events.
 * Returns a cleanup function to stop listening.
 */
export function onMapEvent(
  handler: (event: MapEvent) => void
): () => void {
  return subscribeToEvents((event) => {
    if (event.event_type.startsWith('map.')) {
      handler(event as MapEvent);
    }
  });
}

// ─── Wiki API ─────────────────────────────────────────────────────────────────

export interface WikiFrontmatter {
  type?: string;
  tags?: string[];
  campaign?: string;
  faction?: string;
  disposition?: string;
  standing?: string;
  portrait?: string;
  extends?: string;
  aliases?: string[];
  [key: string]: unknown;
}

export interface WikiPage {
  name: string;
  path: string;
  source: string;
  type: string | null;
  frontmatter: WikiFrontmatter;
  content: string;
}

export interface WikiSearchResult {
  name: string;
  path: string;
  source: string;
  type: string | null;
  score: number;
  snippet: string;
}

export interface WikiPageResponse {
  ok: true;
  page: WikiPage;
}

export interface WikiSearchResponse {
  ok: true;
  query: string;
  count: number;
  results: WikiSearchResult[];
}

export interface WikiListResponse {
  ok: true;
  category: string;
  count: number;
  pages: Array<{
    name: string;
    path: string;
    source: string;
    type: string | null;
    frontmatter: WikiFrontmatter;
  }>;
}

/**
 * Get a wiki page by name.
 */
export async function getWikiPage(
  name: string,
  campaignId?: string
): Promise<WikiPage | null> {
  const params = campaignId ? `?campaign=${encodeURIComponent(campaignId)}` : '';
  const response = await fetch(
    `${BRIDGE_URL}/wiki/page/${encodeURIComponent(name)}${params}`
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Failed to get wiki page: ${response.statusText}`);
  }

  const data: WikiPageResponse = await response.json();
  return data.page;
}

/**
 * Search wiki pages.
 */
export async function searchWiki(
  query: string,
  campaignId?: string,
  limit = 10
): Promise<WikiSearchResult[]> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (campaignId) {
    params.set('campaign', campaignId);
  }

  const response = await fetch(`${BRIDGE_URL}/wiki/search?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to search wiki: ${response.statusText}`);
  }

  const data: WikiSearchResponse = await response.json();
  return data.results;
}

/**
 * List wiki pages in a category.
 */
export async function listWikiPages(
  category: 'npcs' | 'factions' | 'characters' | 'threads' | 'hinges',
  campaignId?: string
): Promise<WikiListResponse['pages']> {
  const params = campaignId ? `?campaign=${encodeURIComponent(campaignId)}` : '';
  const response = await fetch(`${BRIDGE_URL}/wiki/list/${category}${params}`);

  if (!response.ok) {
    throw new Error(`Failed to list wiki pages: ${response.statusText}`);
  }

  const data: WikiListResponse = await response.json();
  return data.pages;
}
