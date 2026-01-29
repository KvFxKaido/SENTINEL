/**
 * Types for the Overworld Canvas View
 * 
 * The overworld makes distance, exposure, and hesitation legible.
 * Movement is free but non-authoritative — proximity alone never commits.
 */

// ============================================================================
// Core Types
// ============================================================================

export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

// ============================================================================
// Entity Types
// ============================================================================

export type EntityType = 'player' | 'npc' | 'hazard' | 'poi' | 'exit';

export interface Entity {
  id: string;
  type: EntityType;
  position: Point;
  radius: number;
  label: string;
  data?: NPCData | HazardData | POIData | ExitData;
}

export interface NPCData {
  name: string;
  faction: string | null;
  disposition: string;
  status: 'active' | 'dormant';
}

export interface HazardData {
  name: string;
  severity: 'minor' | 'moderate' | 'major';
  terrain: string;
}

export interface POIData {
  name: string;
  description: string;
  interactable: boolean;
}

export interface ExitData {
  targetRegion: string;
  direction: 'north' | 'south' | 'east' | 'west';
  traversable: boolean;
  blocked_reason?: string;
}

// ============================================================================
// Region & Terrain
// ============================================================================

export type TerrainType = 
  | 'urban' | 'industrial' | 'road' | 'plains' 
  | 'mountain' | 'forest' | 'water' | 'desert'
  | 'ruins' | 'contaminated' | 'coastal' | 'swamp';

export interface RegionData {
  id: string;
  name: string;
  description: string;
  terrain: TerrainType[];
  primaryFaction: string;
  character: string;
}

// ============================================================================
// Overworld State
// ============================================================================

export interface OverworldState {
  region: RegionData;
  player: {
    position: Point;
    name: string;
  };
  entities: Entity[];
  exits: Entity[];
}

// ============================================================================
// Interaction
// ============================================================================

export interface ProximityPrompt {
  entity: Entity;
  distance: number;
  action: string;
  cost?: string;
}

export interface InteractionState {
  nearbyEntities: Entity[];
  activePrompt: ProximityPrompt | null;
  selectedEntity: Entity | null;
}

// ============================================================================
// Movement
// ============================================================================

export interface MovementState {
  velocity: Point;
  isMoving: boolean;
  direction: 'up' | 'down' | 'left' | 'right' | null;
}

export const MOVEMENT_SPEED = 3;
export const PLAYER_RADIUS = 12;
export const INTERACTION_RADIUS = 50;

// ============================================================================
// Terrain Generation
// ============================================================================

export interface TerrainTile {
  x: number;
  y: number;
  type: TerrainType;
  walkable: boolean;
}

export interface TerrainConfig {
  primary: TerrainType;
  secondary: TerrainType[];
  hazardDensity: number;
  poiDensity: number;
}

export const TERRAIN_CONFIGS: Record<TerrainType, TerrainConfig> = {
  urban: { primary: 'urban', secondary: ['road', 'industrial'], hazardDensity: 0.1, poiDensity: 0.3 },
  industrial: { primary: 'industrial', secondary: ['urban', 'road'], hazardDensity: 0.2, poiDensity: 0.2 },
  road: { primary: 'road', secondary: ['plains', 'urban'], hazardDensity: 0.05, poiDensity: 0.1 },
  plains: { primary: 'plains', secondary: ['road', 'forest'], hazardDensity: 0.05, poiDensity: 0.15 },
  mountain: { primary: 'mountain', secondary: ['forest'], hazardDensity: 0.15, poiDensity: 0.2 },
  forest: { primary: 'forest', secondary: ['mountain', 'plains'], hazardDensity: 0.1, poiDensity: 0.15 },
  water: { primary: 'water', secondary: ['coastal'], hazardDensity: 0.2, poiDensity: 0.1 },
  desert: { primary: 'desert', secondary: ['plains'], hazardDensity: 0.15, poiDensity: 0.1 },
  ruins: { primary: 'ruins', secondary: ['urban', 'contaminated'], hazardDensity: 0.25, poiDensity: 0.3 },
  contaminated: { primary: 'contaminated', secondary: ['ruins', 'industrial'], hazardDensity: 0.4, poiDensity: 0.1 },
  coastal: { primary: 'coastal', secondary: ['water', 'plains'], hazardDensity: 0.1, poiDensity: 0.2 },
  swamp: { primary: 'swamp', secondary: ['water', 'forest'], hazardDensity: 0.2, poiDensity: 0.15 },
};

// ============================================================================
// Color Palette
// ============================================================================

export const COLORS = {
  bg: {
    primary: '#000000',
    secondary: '#0a0a0a',
    tertiary: '#121212',
  },
  terrain: {
    urban: '#1a1a2e',
    industrial: '#16213e',
    road: '#1f1f1f',
    plains: '#1a2f1a',
    mountain: '#2d2d3a',
    forest: '#0d2818',
    water: '#0a1628',
    desert: '#2d2a1a',
    ruins: '#1e1a1a',
    contaminated: '#1a1e1a',
    coastal: '#1a2a2e',
    swamp: '#1a1e1a',
  },
  entity: {
    player: '#56d4dd',
    npc: {
      hostile: '#f85149',
      wary: '#d29922',
      neutral: '#8b949e',
      warm: '#58a6ff',
      loyal: '#3fb950',
    },
    hazard: '#f85149',
    poi: '#f0883e',
    exit: {
      open: '#3fb950',
      blocked: '#f85149',
    },
  },
  ui: {
    prompt: 'rgba(88, 166, 255, 0.9)',
    promptBg: 'rgba(0, 0, 0, 0.8)',
  },
};

// ============================================================================
// Hazard Templates
// ============================================================================

export const HAZARD_TEMPLATES: Record<TerrainType, string[]> = {
  urban: ['Collapsed Building', 'Gang Territory', 'Checkpoint'],
  industrial: ['Toxic Spill', 'Unstable Structure', 'Automated Security'],
  road: ['Bandit Ambush', 'Roadblock', 'Wrecked Convoy'],
  plains: ['Exposed Position', 'Patrol Route', 'Sniper Nest'],
  mountain: ['Rockslide Zone', 'Thin Air', 'Narrow Pass'],
  forest: ['Wildlife', 'Hidden Camp', 'Overgrown Path'],
  water: ['Strong Current', 'Contaminated Water', 'Patrol Boat'],
  desert: ['Heat Exposure', 'Sandstorm Zone', 'No Cover'],
  ruins: ['Structural Collapse', 'Scavenger Camp', 'Radiation Pocket'],
  contaminated: ['Radiation Zone', 'Chemical Leak', 'Mutant Territory'],
  coastal: ['Tidal Zone', 'Smuggler Watch', 'Eroded Cliff'],
  swamp: ['Quicksand', 'Disease Vector', 'Hidden Depths'],
};

// ============================================================================
// POI Templates
// ============================================================================

export const POI_TEMPLATES: Record<TerrainType, string[]> = {
  urban: ['Abandoned Shop', 'Safe House', 'Information Broker', 'Black Market'],
  industrial: ['Salvage Yard', 'Power Station', 'Factory Floor', 'Warehouse'],
  road: ['Rest Stop', 'Trading Post', 'Fuel Cache', 'Waystation'],
  plains: ['Farmstead', 'Water Well', 'Observation Point', 'Camp Site'],
  mountain: ['Mining Camp', 'Hidden Valley', 'Lookout Post', 'Cave System'],
  forest: ['Hunter Camp', 'Hidden Grove', 'Ranger Station', 'Old Trail'],
  water: ['Dock', 'Fishing Spot', 'Island', 'Underwater Cache'],
  desert: ['Oasis', 'Buried Cache', 'Nomad Camp', 'Ancient Ruin'],
  ruins: ['Vault', 'Archive', 'Bunker', 'Memorial'],
  contaminated: ['Research Lab', 'Quarantine Zone', 'Decon Station', 'Hot Zone Edge'],
  coastal: ['Harbor', 'Lighthouse', 'Smuggler Cove', 'Beach Camp'],
  swamp: ['Stilted Village', 'Herbalist Hut', 'Sunken Ruin', 'Dry Ground'],
};
