// SENTINEL World Map Types
// Canonical direction: Python (schema.py) -> TypeScript
// These types match the bridge API response shapes.

export type RegionConnectivity = 'disconnected' | 'aware' | 'connected' | 'embedded';

export type Faction =
  | 'nexus'
  | 'ember_colonies'
  | 'lattice'
  | 'convergence'
  | 'covenant'
  | 'wanderers'
  | 'cultivators'
  | 'steel_syndicate'
  | 'witnesses'
  | 'architects'
  | 'ghost_networks';

export type Region =
  | 'frozen_edge'
  | 'pacific_corridor'
  | 'northern_reaches'
  | 'rust_corridor'
  | 'breadbasket'
  | 'northeast_scar'
  | 'desert_sprawl'
  | 'appalachian_hollows'
  | 'texas_spine'
  | 'gulf_passage'
  | 'sovereign_south';

export interface RouteRequirement {
  type: 'faction' | 'vehicle' | 'contact' | 'story' | 'hazard';
  faction?: Faction;
  min_standing?: string;
  vehicle_capability?: string;
  description?: string;
  met?: boolean;
}

export interface RouteAlternative {
  type: string;
  description: string;
  faction?: Faction;
  cost?: { social_energy?: number; credits?: number; time?: string };
  consequence?: string;
  available?: boolean;
}

export interface Route {
  to: Region;
  requirements: RouteRequirement[];
  alternatives?: RouteAlternative[];
  terrain: string[];
  travel_description: string;
  contested?: boolean;
  risky?: boolean;
}

export interface RegionData {
  id: Region;
  name: string;
  description: string;
  primary_faction: Faction;
  contested_by?: Faction[];
  terrain: string[];
  character: string;
  routes: Route[];
  nexus_presence: 'low' | 'medium' | 'high';
  hazards: string[];
  points_of_interest: string[];
  position: { x: number; y: number };
}

export interface ContentMarker {
  type: 'current' | 'job' | 'thread' | 'npc' | 'locked' | 'risky';
  count?: number;
}

// Faction display metadata (colors, names)
export interface FactionInfo {
  id: Faction;
  name: string;
  shortName: string;
  color: string;
}

// Static faction colors — these never change
export const FACTION_COLORS: Record<Faction, string> = {
  nexus: '#a855f7',
  ember_colonies: '#f97316',
  lattice: '#3b82f6',
  convergence: '#06b6d4',
  covenant: '#eab308',
  wanderers: '#22c55e',
  cultivators: '#10b981',
  steel_syndicate: '#ef4444',
  witnesses: '#f59e0b',
  architects: '#6366f1',
  ghost_networks: '#6b7280',
};

export const FACTION_INFO: Record<Faction, FactionInfo> = {
  nexus: { id: 'nexus', name: 'Nexus', shortName: 'Nexus', color: '#a855f7' },
  ember_colonies: { id: 'ember_colonies', name: 'Ember Colonies', shortName: 'Ember', color: '#f97316' },
  lattice: { id: 'lattice', name: 'Lattice', shortName: 'Lattice', color: '#3b82f6' },
  convergence: { id: 'convergence', name: 'Convergence', shortName: 'Conv.', color: '#06b6d4' },
  covenant: { id: 'covenant', name: 'Covenant', shortName: 'Covenant', color: '#eab308' },
  wanderers: { id: 'wanderers', name: 'Wanderers', shortName: 'Wand.', color: '#22c55e' },
  cultivators: { id: 'cultivators', name: 'Cultivators', shortName: 'Cult.', color: '#10b981' },
  steel_syndicate: { id: 'steel_syndicate', name: 'Steel Syndicate', shortName: 'Steel', color: '#ef4444' },
  witnesses: { id: 'witnesses', name: 'Witnesses', shortName: 'Wit.', color: '#f59e0b' },
  architects: { id: 'architects', name: 'Architects', shortName: 'Arch.', color: '#6366f1' },
  ghost_networks: { id: 'ghost_networks', name: 'Ghost Networks', shortName: 'Ghost', color: '#6b7280' },
};
