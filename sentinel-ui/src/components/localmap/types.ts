/**
 * Types for Local Map System (Phase 2)
 * 
 * Local maps are small, authored spaces where real-time exploration happens.
 * Fixed isometric perspective with tile-based collision.
 * 
 * Design Constraints:
 * - Small, authored rooms only (no procedural generation)
 * - Clear occlusion rules (walls fade when blocking player)
 * - Gridless movement with tile-based collision
 */

// ============================================================================
// Core Types
// ============================================================================

export interface Point {
  x: number;
  y: number;
}

export interface GridPosition {
  col: number;
  row: number;
}

// ============================================================================
// Tile System
// ============================================================================

export enum TileType {
  FLOOR = 0,
  WALL = 1,
  WALL_LOW = 2,      // Half-height wall, can see over
  DOOR = 3,
  DOOR_LOCKED = 4,
  EXIT = 5,
  WATER = 6,
  PIT = 7,
  COVER_FULL = 8,    // Full cover for combat
  COVER_HALF = 9,    // Half cover
  STAIRS_UP = 10,
  STAIRS_DOWN = 11,
  DEBRIS = 12,       // Slows movement
  TERMINAL = 13,     // Interactive object
  CONTAINER = 14,    // Lootable
}

export interface TileProperties {
  walkable: boolean;
  blocksSight: boolean;
  blocksProjectiles: boolean;
  movementCost: number;  // 1 = normal, 2 = slow, 0 = impassable
  interactable: boolean;
  coverValue: number;    // 0 = none, 1 = half, 2 = full
}

export const TILE_PROPERTIES: Record<TileType, TileProperties> = {
  [TileType.FLOOR]:       { walkable: true,  blocksSight: false, blocksProjectiles: false, movementCost: 1, interactable: false, coverValue: 0 },
  [TileType.WALL]:        { walkable: false, blocksSight: true,  blocksProjectiles: true,  movementCost: 0, interactable: false, coverValue: 2 },
  [TileType.WALL_LOW]:    { walkable: false, blocksSight: false, blocksProjectiles: true,  movementCost: 0, interactable: false, coverValue: 1 },
  [TileType.DOOR]:        { walkable: true,  blocksSight: false, blocksProjectiles: false, movementCost: 1, interactable: true,  coverValue: 0 },
  [TileType.DOOR_LOCKED]: { walkable: false, blocksSight: true,  blocksProjectiles: true,  movementCost: 0, interactable: true,  coverValue: 2 },
  [TileType.EXIT]:        { walkable: true,  blocksSight: false, blocksProjectiles: false, movementCost: 1, interactable: true,  coverValue: 0 },
  [TileType.WATER]:       { walkable: false, blocksSight: false, blocksProjectiles: false, movementCost: 0, interactable: false, coverValue: 0 },
  [TileType.PIT]:         { walkable: false, blocksSight: false, blocksProjectiles: false, movementCost: 0, interactable: false, coverValue: 0 },
  [TileType.COVER_FULL]:  { walkable: false, blocksSight: false, blocksProjectiles: true,  movementCost: 0, interactable: false, coverValue: 2 },
  [TileType.COVER_HALF]:  { walkable: false, blocksSight: false, blocksProjectiles: false, movementCost: 0, interactable: false, coverValue: 1 },
  [TileType.STAIRS_UP]:   { walkable: true,  blocksSight: false, blocksProjectiles: false, movementCost: 1, interactable: true,  coverValue: 0 },
  [TileType.STAIRS_DOWN]: { walkable: true,  blocksSight: false, blocksProjectiles: false, movementCost: 1, interactable: true,  coverValue: 0 },
  [TileType.DEBRIS]:      { walkable: true,  blocksSight: false, blocksProjectiles: false, movementCost: 2, interactable: false, coverValue: 1 },
  [TileType.TERMINAL]:    { walkable: false, blocksSight: false, blocksProjectiles: false, movementCost: 0, interactable: true,  coverValue: 0 },
  [TileType.CONTAINER]:   { walkable: false, blocksSight: false, blocksProjectiles: false, movementCost: 0, interactable: true,  coverValue: 0 },
};

// ============================================================================
// Map Objects
// ============================================================================

export interface MapObject {
  id: string;
  type: 'npc' | 'item' | 'prop' | 'trigger';
  position: GridPosition;
  name: string;
  interactionDisabled?: boolean;
  data?: NPCObjectData | ItemObjectData | PropObjectData | TriggerObjectData;
}

export enum NPCBehaviorState {
  IDLE = 'idle',
  BUSY = 'busy',
  UNAVAILABLE = 'unavailable',
  AWARE = 'aware',
  ALERT = 'alert',
}

export interface NPCObjectData {
  npcId: string;
  faction: string | null;
  disposition: string;
  patrolRoute?: GridPosition[];
  facing?: 'north' | 'south' | 'east' | 'west';
  behaviorState?: NPCBehaviorState;
  awarenessOf?: string | null;
  lingerTimer?: number;
  glanceInterval?: number;
  fleeOnApproach?: boolean;
}

export interface ItemObjectData {
  itemId: string;
  quantity: number;
  hidden: boolean;
}

export interface PropObjectData {
  propType: string;
  interactable: boolean;
  state?: string;
}

export interface TriggerObjectData {
  triggerId: string;
  condition: string;
  effect: string;
  oneShot: boolean;
  triggered: boolean;
}

// ============================================================================
// Exit System
// ============================================================================

export interface MapExit {
  id: string;
  position: GridPosition;
  direction: 'north' | 'south' | 'east' | 'west' | 'up' | 'down';
  targetMap: string;
  targetSpawn: string;  // Spawn point ID in target map
  label: string;
  locked: boolean;
  lockReason?: string;
  requiresKey?: string;
}

export interface SpawnPoint {
  id: string;
  position: GridPosition;
  facing: 'north' | 'south' | 'east' | 'west';
  isDefault: boolean;
}

// ============================================================================
// Local Map Definition
// ============================================================================

export interface LocalMapTemplate {
  id: string;
  name: string;
  regionId: string;
  description: string;
  
  // Grid dimensions
  width: number;   // In tiles
  height: number;  // In tiles
  tileSize: number; // Pixels per tile (default 32)
  
  // Tile data (2D array, row-major)
  tiles: TileType[][];
  
  // Map elements
  objects: MapObject[];
  exits: MapExit[];
  spawnPoints: SpawnPoint[];
  
  // Lighting & atmosphere
  ambientLight: number;  // 0-1, affects visibility
  atmosphere: 'neutral' | 'tense' | 'hostile' | 'safe';

  // Cold zones suppress interaction feedback
  coldZones?: ColdZone[];
  
  // Metadata
  author?: string;
  version?: number;
}

// ============================================================================
// Runtime State
// ============================================================================

export interface LocalMapState {
  template: LocalMapTemplate;
  
  // Dynamic state
  doorsOpen: Set<string>;      // IDs of open doors
  containersLooted: Set<string>;
  triggersActivated: Set<string>;
  
  // Entity positions (updated at runtime)
  npcPositions: Map<string, Point>;
  playerPosition: Point;
  playerFacing: 'north' | 'south' | 'east' | 'west';
}

// ============================================================================
// Cold Zones
// ============================================================================

export interface ColdZone {
  id: string;
  name: string;
  bounds: {
    col: number;
    row: number;
    width: number;
    height: number;
  };
  suppressPrompts?: boolean;
  suppressDialogue?: boolean;
}

// ============================================================================
// Rendering Configuration
// ============================================================================

export const TILE_SIZE = 32;  // Base tile size in pixels

export const TILE_COLORS: Record<TileType, string> = {
  [TileType.FLOOR]:       '#1a1a2e',
  [TileType.WALL]:        '#2d2d3a',
  [TileType.WALL_LOW]:    '#252530',
  [TileType.DOOR]:        '#3a3a4a',
  [TileType.DOOR_LOCKED]: '#4a3a3a',
  [TileType.EXIT]:        '#1a3a2e',
  [TileType.WATER]:       '#0a1628',
  [TileType.PIT]:         '#0a0a0a',
  [TileType.COVER_FULL]:  '#2a2a3a',
  [TileType.COVER_HALF]:  '#252535',
  [TileType.STAIRS_UP]:   '#2a3a2a',
  [TileType.STAIRS_DOWN]: '#2a2a3a',
  [TileType.DEBRIS]:      '#252520',
  [TileType.TERMINAL]:    '#1a2a3a',
  [TileType.CONTAINER]:   '#3a3020',
};

export const ENTITY_COLORS = {
  player: '#56d4dd',
  npc: {
    hostile: '#f85149',
    wary: '#d29922',
    neutral: '#8b949e',
    warm: '#58a6ff',
    loyal: '#3fb950',
  },
  item: '#f0883e',
  prop: '#6e7681',
  exit: {
    open: '#3fb950',
    locked: '#f85149',
  },
};

// ============================================================================
// Movement Constants
// ============================================================================

export const MOVEMENT_SPEED = 4;        // Pixels per frame
export const PLAYER_RADIUS = 10;        // Collision radius
export const INTERACTION_RANGE = 48;    // Pixels to trigger interaction prompt
export const NPC_DETECTION_RANGE = 128; // Pixels for NPC awareness
