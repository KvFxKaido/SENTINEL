/**
 * Phase 4 Expansion Types
 * 
 * Multi-region overworlds, faction pressure visualization, and combat integration.
 */

// ============================================================================
// Region Transition
// ============================================================================

export interface RegionTransition {
  fromRegion: string;
  toRegion: string;
  direction: 'north' | 'south' | 'east' | 'west';
  cost: number; // turns
  consequence?: string;
}

export interface TransitionState {
  isTransitioning: boolean;
  progress: number; // 0-100
  transition: RegionTransition | null;
}

// ============================================================================
// Faction Pressure
// ============================================================================

export type FactionInfluence = 'dominant' | 'strong' | 'contested' | 'weak' | 'none';

export interface FactionZone {
  id: string;
  faction: string;
  influence: FactionInfluence;
  bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  color: string;
}

export interface FactionPressure {
  primaryFaction: string;
  primaryInfluence: FactionInfluence;
  contestedBy: Array<{
    faction: string;
    influence: FactionInfluence;
  }>;
  zones: FactionZone[];
}

export const FACTION_COLORS: Record<string, string> = {
  nexus: '#58a6ff',
  ember_colonies: '#f0883e',
  lattice: '#a371f7',
  convergence: '#56d4dd',
  covenant: '#d2a8ff',
  wanderers: '#7ee787',
  cultivators: '#3fb950',
  steel_syndicate: '#8b949e',
  witnesses: '#f8e3a1',
  architects: '#79c0ff',
  ghost_networks: '#6e7681',
};

export const INFLUENCE_OPACITY: Record<FactionInfluence, number> = {
  dominant: 0.25,
  strong: 0.18,
  contested: 0.12,
  weak: 0.06,
  none: 0,
};

// ============================================================================
// Combat System
// ============================================================================

export type CombatPhase = 'initiative' | 'player_turn' | 'enemy_turn' | 'resolution';

export interface Combatant {
  id: string;
  name: string;
  type: 'player' | 'npc' | 'hostile';
  health: number;
  maxHealth: number;
  energy: number;
  maxEnergy: number;
  position: { x: number; y: number };
  faction?: string;
  disposition?: string;
}

export interface CombatAction {
  id: string;
  name: string;
  type: 'attack' | 'defend' | 'ability' | 'item' | 'flee';
  cost: number; // energy cost
  description: string;
  targetType: 'single' | 'area' | 'self';
}

export interface CombatState {
  active: boolean;
  phase: CombatPhase;
  turn: number;
  combatants: Combatant[];
  currentCombatant: string | null;
  selectedAction: CombatAction | null;
  selectedTarget: string | null;
  log: CombatLogEntry[];
  outcome: CombatOutcome | null;
}

export interface CombatLogEntry {
  turn: number;
  actor: string;
  action: string;
  target?: string;
  result: string;
  damage?: number;
}

export interface CombatOutcome {
  victory: boolean;
  fled: boolean;
  consequences: string[];
  rewards?: string[];
  casualties?: string[];
}

// Default combat actions available to player
export const PLAYER_ACTIONS: CombatAction[] = [
  {
    id: 'strike',
    name: 'Strike',
    type: 'attack',
    cost: 1,
    description: 'A basic melee attack',
    targetType: 'single',
  },
  {
    id: 'shoot',
    name: 'Shoot',
    type: 'attack',
    cost: 2,
    description: 'Ranged attack with equipped weapon',
    targetType: 'single',
  },
  {
    id: 'defend',
    name: 'Defend',
    type: 'defend',
    cost: 1,
    description: 'Reduce incoming damage this turn',
    targetType: 'self',
  },
  {
    id: 'assess',
    name: 'Assess',
    type: 'ability',
    cost: 0,
    description: 'Study the enemy for weaknesses',
    targetType: 'single',
  },
  {
    id: 'flee',
    name: 'Flee',
    type: 'flee',
    cost: 3,
    description: 'Attempt to escape combat',
    targetType: 'self',
  },
];

// ============================================================================
// Encounter System
// ============================================================================

export type EncounterType = 'hostile' | 'neutral' | 'ambush' | 'patrol';

export interface Encounter {
  id: string;
  type: EncounterType;
  faction?: string;
  hostiles: Array<{
    name: string;
    health: number;
    threat: 'low' | 'medium' | 'high';
  }>;
  canAvoid: boolean;
  avoidCost?: { type: string; amount: number };
  triggerDistance: number;
}

// ============================================================================
// Mini-map for Multi-region
// ============================================================================

export interface MiniMapRegion {
  id: string;
  name: string;
  position: { x: number; y: number };
  isCurrent: boolean;
  isConnected: boolean;
  primaryFaction: string;
}

export interface MiniMapState {
  regions: MiniMapRegion[];
  currentRegion: string;
  playerPosition: { x: number; y: number };
}
