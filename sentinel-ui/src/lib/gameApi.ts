const GAME_API_URL = import.meta.env.PUBLIC_GAME_API_URL || 'http://localhost:8000';

export type DialogueTone = 'neutral' | 'aggressive' | 'empathetic' | 'deceptive';

export interface SocialEnergyState {
  current: number;
  max: number;
  percentage?: number;
}

export interface DialogueOption {
  id: string;
  text: string;
  tone: DialogueTone;
  social_cost: number;
  risk_hint?: string;
}

export interface DialogueResponse {
  npc_id?: string;
  npc_name?: string;
  npc_faction?: string | null;
  dialogue_text: string;
  options: DialogueOption[];
  social_energy_cost: number;
  disposition_change?: number;
  ended_by_npc?: boolean;
  memory_tags?: string[];
  social_energy?: SocialEnergyState;
  state_version?: number;
  error?: string;
  meta?: {
    mock?: boolean;
  };
}

export interface CombatActionPayload {
  action: string;
  actor_id: string;
  target_id?: string;
  target_position?: { x: number; y: number };
  round?: number;
  state_version?: number;
}

export interface CombatActionResult {
  ok: boolean;
  action?: CombatActionPayload;
  hit?: boolean;
  injury?: string;
  target_status?: string;
  outcome?: string;
  summary?: string;
  state_version?: number;
  error?: string;
  meta?: {
    mock?: boolean;
  };
}

export interface CombatEndPayload {
  outcome: string;
  faction_impact?: Record<string, number>;
  injuries?: Record<string, unknown>;
  rounds?: number;
  state_version?: number;
}

export interface CombatEndResult {
  ok: boolean;
  outcome: string;
  faction_impact?: Record<string, number>;
  injuries?: Record<string, unknown>;
  rounds?: number;
  state_version?: number;
  error?: string;
  meta?: {
    mock?: boolean;
  };
}

export interface GameStateResponse {
  ok: boolean;
  version?: number;
  state_version?: number;
  character?: {
    social_energy?: SocialEnergyState;
  } | null;
  error?: string;
}

export interface FactionPressureApi {
  faction_id: string;
  faction_name?: string;
  standing?: string;
  reputation?: number;
  pressure_level?: number;
  level?: number;
}

export interface PendingThreadApi {
  id: string;
  trigger: string;
  severity: string;
  age_sessions?: number;
  description?: string;
  faction_id?: string;
  created_minutes?: number;
  spatial?: {
    mapId?: string;
    map_id?: string;
    position?: { col: number; row: number };
    col?: number;
    row?: number;
  };
}

export interface ConsequenceActivationApi {
  id: string;
  type?: string;
  headline?: string;
  description?: string;
  faction_id?: string;
  npc_id?: string;
  map_id?: string;
  position?: { col: number; row: number };
  timestamp?: number;
  severity?: 'info' | 'warning' | 'critical';
}

export interface ConsequenceState {
  ok: boolean;
  pressures: FactionPressureApi[];
  pending_threads: PendingThreadApi[];
  recent_activations: ConsequenceActivationApi[];
  meta?: {
    mock?: boolean;
  };
}

let stateVersion = 0;

function updateStateVersion(data: Record<string, unknown> | null, response?: Response) {
  const headerVersion = response?.headers.get('x-state-version') || response?.headers.get('X-State-Version');
  const parsedHeader = headerVersion ? Number(headerVersion) : null;
  const bodyVersion = typeof data?.state_version === 'number'
    ? data?.state_version
    : typeof data?.version === 'number'
      ? data?.version
      : null;

  const nextVersion = Number.isFinite(parsedHeader) ? parsedHeader : bodyVersion;
  if (typeof nextVersion === 'number' && nextVersion >= stateVersion) {
    stateVersion = nextVersion;
  }
}

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<{ data: T; response: Response }> {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('X-State-Version')) {
    headers.set('X-State-Version', String(stateVersion));
    headers.set('state_version', String(stateVersion));
  }

  const response = await fetch(`${GAME_API_URL}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json();
  updateStateVersion(data, response);
  return { data, response };
}

function normalizeDialogueResponse(raw: Record<string, unknown>): DialogueResponse {
  const optionsRaw = Array.isArray(raw.options) ? raw.options : [];
  const allowedTones: DialogueTone[] = ['neutral', 'aggressive', 'empathetic', 'deceptive'];
  const options: DialogueOption[] = optionsRaw.map((option: any) => {
    const consequences = Array.isArray(option.consequences) ? option.consequences : [];
    const toneValue = typeof option.tone === 'string' && allowedTones.includes(option.tone as DialogueTone)
      ? (option.tone as DialogueTone)
      : 'neutral';
    return {
      id: String(option.id ?? ''),
      text: String(option.text ?? ''),
      tone: toneValue,
      social_cost: typeof option.social_cost === 'number'
        ? option.social_cost
        : typeof option.socialCost === 'number'
          ? option.socialCost
          : 0,
      risk_hint: typeof option.risk_hint === 'string'
        ? option.risk_hint
        : typeof option.riskHint === 'string'
          ? option.riskHint
          : typeof consequences[0] === 'string'
            ? consequences[0]
            : undefined,
    };
  });

  return {
    npc_id: typeof raw.npc_id === 'string' ? raw.npc_id : undefined,
    npc_name: typeof raw.npc_name === 'string' ? raw.npc_name : undefined,
    npc_faction: typeof raw.npc_faction === 'string' ? raw.npc_faction : undefined,
    dialogue_text: typeof raw.dialogue_text === 'string'
      ? raw.dialogue_text
      : typeof raw.npc_response === 'string'
        ? raw.npc_response
        : '',
    options,
    social_energy_cost: typeof raw.social_energy_cost === 'number'
      ? raw.social_energy_cost
      : 0,
    disposition_change: typeof raw.disposition_change === 'number'
      ? raw.disposition_change
      : undefined,
    ended_by_npc: raw.ended_by_npc === true
      || (raw.dialogue_ended === true && raw.end_reason === 'npc_ended'),
    memory_tags: Array.isArray(raw.memory_tags) ? raw.memory_tags.map(tag => String(tag)) : undefined,
    social_energy: raw.social_energy as SocialEnergyState | undefined,
    state_version: typeof raw.state_version === 'number' ? raw.state_version : undefined,
    error: typeof raw.error === 'string' ? raw.error : undefined,
  };
}

function normalizeCombatActionResponse(
  raw: Record<string, unknown>,
  fallbackAction: CombatActionPayload
): CombatActionResult {
  const action = (raw.action as CombatActionPayload) || fallbackAction;
  return {
    ok: raw.ok !== false,
    action,
    hit: raw.hit === true ? true : raw.hit === false ? false : undefined,
    injury: typeof raw.injury === 'string' ? raw.injury : undefined,
    target_status: typeof raw.target_status === 'string' ? raw.target_status : undefined,
    outcome: typeof raw.outcome === 'string' ? raw.outcome : undefined,
    summary: typeof raw.summary === 'string' ? raw.summary : undefined,
    state_version: typeof raw.state_version === 'number' ? raw.state_version : undefined,
    error: typeof raw.error === 'string' ? raw.error : undefined,
    meta: raw.meta as { mock?: boolean } | undefined,
  };
}

function normalizeCombatEndResponse(
  raw: Record<string, unknown>,
  fallbackOutcome: string
): CombatEndResult {
  return {
    ok: raw.ok !== false,
    outcome: typeof raw.outcome === 'string' ? raw.outcome : fallbackOutcome,
    faction_impact: typeof raw.faction_impact === 'object' && raw.faction_impact !== null
      ? (raw.faction_impact as Record<string, number>)
      : undefined,
    injuries: typeof raw.injuries === 'object' && raw.injuries !== null
      ? (raw.injuries as Record<string, unknown>)
      : undefined,
    rounds: typeof raw.rounds === 'number' ? raw.rounds : undefined,
    state_version: typeof raw.state_version === 'number' ? raw.state_version : undefined,
    error: typeof raw.error === 'string' ? raw.error : undefined,
    meta: raw.meta as { mock?: boolean } | undefined,
  };
}

function mockDialogue(npcId: string, optionId?: string): DialogueResponse {
  if (optionId === 'end') {
    return {
      npc_id: npcId,
      dialogue_text: 'The NPC turns away without another word.',
      options: [],
      social_energy_cost: 1,
      ended_by_npc: true,
      meta: { mock: true },
    };
  }

  return {
    npc_id: npcId,
    dialogue_text: 'The reply is cautious and uneven, like the place itself.',
    options: [
      {
        id: 'neutral',
        text: 'Ask about the area',
        tone: 'neutral',
        social_cost: 3,
        risk_hint: 'May get half-answers.',
      },
      {
        id: 'empathetic',
        text: 'Offer help',
        tone: 'empathetic',
        social_cost: 5,
        risk_hint: 'Could soften their stance.',
      },
      {
        id: 'end',
        text: 'End the conversation',
        tone: 'neutral',
        social_cost: 1,
      },
    ],
    social_energy_cost: 2,
    disposition_change: 0,
    ended_by_npc: false,
    memory_tags: ['timestamped', 'location_shift'],
    meta: { mock: true },
  };
}

function mockConsequences(mapId: string): ConsequenceState {
  const seed = Math.abs(hashString(mapId));
  const level = 35 + (seed % 50);
  const factionIds = ['steel_syndicate', 'lattice', 'ember_colonies', 'ghost_networks'];
  const factionId = factionIds[seed % factionIds.length];

  return {
    ok: true,
    pressures: [
      {
        faction_id: factionId,
        faction_name: factionId.replace(/_/g, ' '),
        standing: 'neutral',
        reputation: level - 50,
        pressure_level: Math.round(level / 20),
        level,
      },
    ],
    pending_threads: [
      {
        id: `thread-${seed % 999}`,
        trigger: 'When the player returns to the market corridor',
        severity: 'moderate',
        description: 'A quiet patrol exchange has shifted the balance.',
        faction_id: factionId,
        created_minutes: 120,
        spatial: {
          map_id: mapId,
          position: { col: 6 + (seed % 4), row: 4 + (seed % 3) },
        },
      },
    ],
    recent_activations: [],
    meta: { mock: true },
  };
}

function mockCombatAction(action: CombatActionPayload): CombatActionResult {
  const hit = Math.random() > 0.4;
  return {
    ok: true,
    action,
    hit,
    injury: hit ? 'minor injury' : undefined,
    summary: hit ? 'A hit lands.' : 'The shot goes wide.',
    meta: { mock: true },
  };
}

function mockCombatEnd(outcome: string): CombatEndResult {
  return {
    ok: true,
    outcome,
    meta: { mock: true },
  };
}

export async function getState(): Promise<GameStateResponse> {
  try {
    const { data } = await requestJson<GameStateResponse>('/state');
    if (data && typeof data === 'object') {
      const version = typeof data.state_version === 'number' ? data.state_version : data.version;
      if (typeof version === 'number') {
        stateVersion = Math.max(stateVersion, version);
      }
    }
    return data;
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Failed to reach game API' };
  }
}

export async function startDialogue(npcId: string, campaignId: string): Promise<DialogueResponse> {
  const payload = {
    npc_id: npcId,
    campaign_id: campaignId || undefined,
    context: campaignId ? `campaign:${campaignId}` : '',
    player_message: '',
    player_intent: '',
    state_version: stateVersion,
  };

  try {
    const { data } = await requestJson<Record<string, unknown>>('/dialogue', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return normalizeDialogueResponse(data || {});
  } catch (error) {
    const response = mockDialogue(npcId);
    return {
      ...response,
      error: 'Connection lost',
    };
  }
}

export async function continueDialogue(
  npcId: string,
  optionId: string,
  playerMessage?: string
): Promise<DialogueResponse> {
  const payload = {
    npc_id: npcId,
    context: `option:${optionId}`,
    player_message: playerMessage || '',
    player_intent: playerMessage || '',
    option_id: optionId,
    state_version: stateVersion,
  };

  try {
    const { data } = await requestJson<Record<string, unknown>>('/dialogue', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return normalizeDialogueResponse(data || {});
  } catch (error) {
    const response = mockDialogue(npcId, optionId);
    return {
      ...response,
      error: 'Connection lost',
    };
  }
}

export async function resolveCombatAction(
  action: CombatActionPayload,
  targetId?: string
): Promise<CombatActionResult> {
  const payload: CombatActionPayload = {
    ...action,
    target_id: targetId || action.target_id,
    state_version: stateVersion,
  };

  try {
    const { data } = await requestJson<Record<string, unknown>>('/combat/action', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return normalizeCombatActionResponse(data || {}, payload);
  } catch (error) {
    const response = mockCombatAction(payload);
    return {
      ...response,
      error: 'Connection lost',
    };
  }
}

export async function endCombat(payload: CombatEndPayload): Promise<CombatEndResult> {
  const requestPayload: CombatEndPayload = {
    ...payload,
    state_version: stateVersion,
  };

  try {
    const { data } = await requestJson<Record<string, unknown>>('/combat/end', {
      method: 'POST',
      body: JSON.stringify(requestPayload),
    });
    return normalizeCombatEndResponse(data || {}, payload.outcome);
  } catch (error) {
    const response = mockCombatEnd(payload.outcome);
    return {
      ...response,
      error: 'Connection lost',
    };
  }
}

export async function getConsequences(
  mapId: string,
  campaignId: string
): Promise<ConsequenceState> {
  const query = new URLSearchParams();
  if (mapId) query.set('mapId', mapId);
  if (campaignId) query.set('campaignId', campaignId);

  try {
    const [pressureRes, consequenceRes] = await Promise.all([
      requestJson<Record<string, unknown>>('/factions/pressure'),
      requestJson<Record<string, unknown>>(`/consequences/check?${query.toString()}`),
    ]);

    const rawPressures = (pressureRes.data as any)?.pressures;
    const pressures = Array.isArray(rawPressures)
      ? (rawPressures as FactionPressureApi[]).map(entry => ({
          ...entry,
          level: typeof entry.level === 'number'
            ? entry.level
            : typeof entry.pressure_level === 'number'
              ? entry.pressure_level * 20
              : typeof entry.reputation === 'number'
                ? Math.min(100, Math.abs(entry.reputation))
                : 0,
        }))
      : [];

    const pending_threads = Array.isArray((consequenceRes.data as any)?.pending_threads)
      ? ((consequenceRes.data as any).pending_threads as PendingThreadApi[])
      : [];

    const recent_activations = Array.isArray((consequenceRes.data as any)?.recent_activations)
      ? ((consequenceRes.data as any).recent_activations as ConsequenceActivationApi[])
      : [];

    return {
      ok: true,
      pressures,
      pending_threads,
      recent_activations,
    };
  } catch (error) {
    return mockConsequences(mapId);
  }
}

export async function acknowledgeNotification(notificationId: string): Promise<void> {
  if (!notificationId) return;

  try {
    await requestJson<Record<string, unknown>>('/consequences/acknowledge', {
      method: 'POST',
      body: JSON.stringify({ notification_id: notificationId, state_version: stateVersion }),
    });
  } catch (error) {
    // Ignore acknowledgement failures in mock mode.
  }
}

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}
