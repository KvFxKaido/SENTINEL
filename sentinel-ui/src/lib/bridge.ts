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
    };
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

export interface CommandResult {
  type: 'result';
  ok: boolean;
  error?: string;
  response?: string;
  result?: string;
  output?: string;
  campaign?: {
    id: string;
    name: string;
    session: number;
  };
  [key: string]: unknown;
}

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

export interface CampaignState {
  ok: boolean;
  error?: string;
  campaign?: {
    id: string;
    name: string;
    session: number;
    phase: number;
  };
  character?: {
    name: string | null;
    background: string | null;
    social_energy: {
      current: number;
      max: number;
    };
    credits: number;
    gear: GearItem[];
    enhancements: Enhancement[];
  };
  region: string;
  location: string;
  session_phase: string | null;
  loadout: string[];
  factions: Array<{
    id: string;
    name: string;
    standing: string;
  }>;
  active_jobs: number;
  dormant_threads: number;
}

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
  const result = await sendCommand('campaign_state');
  return result as unknown as CampaignState;
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
