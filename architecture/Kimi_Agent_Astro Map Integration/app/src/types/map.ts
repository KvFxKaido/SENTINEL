// SENTINEL World Map Types

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
  minStanding?: string;
  vehicleCapability?: string;
  description?: string;
}

export interface RouteAlternative {
  type: string;
  description: string;
  faction?: Faction;
  cost?: { social_energy?: number; credits?: number; time?: string };
  consequence?: string;
}

export interface Route {
  to: Region;
  requirements: RouteRequirement[];
  alternatives?: RouteAlternative[];
  terrain: string[];
  travelDescription: string;
  contested?: boolean;
  risky?: boolean;
}

export interface RegionData {
  id: Region;
  name: string;
  description: string;
  primaryFaction: Faction;
  contestedBy?: Faction[];
  terrain: string[];
  character: string;
  routes: Route[];
  nexusPresence: 'low' | 'medium' | 'high';
  hazards: string[];
  pointsOfInterest: string[];
  // Position on map (0-100 percentages)
  position: { x: number; y: number };
}

export interface RegionState {
  connectivity: RegionConnectivity;
  npcsMet: string[];
  threadsResolved: string[];
  significantJobs: string[];
  notes?: string;
  secretsFound: string[];
}

export interface ContentMarker {
  type: 'current' | 'job' | 'thread' | 'npc' | 'locked' | 'risky';
  count?: number;
}

export interface FactionData {
  id: Faction;
  name: string;
  shortName: string;
  motto: string;
  color: string;
  description: string;
}
