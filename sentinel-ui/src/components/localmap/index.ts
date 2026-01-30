/**
 * Local Map Module (Phase 2)
 * 
 * Tile-based local map system for real-time exploration.
 */

// Main components
export { LocalMapCanvas } from './LocalMapCanvas';
export { LocalMapView } from './LocalMapView';
export { FactionPressureOverlay } from './FactionPressureOverlay';
export { NotificationSystem } from './NotificationSystem';

// Types
export type {
  Point,
  GridPosition,
  TileType,
  TileProperties,
  MapObject,
  NPCObjectData,
  NPCBehaviorState,
  ItemObjectData,
  PropObjectData,
  TriggerObjectData,
  MapExit,
  SpawnPoint,
  LocalMapTemplate,
  LocalMapState,
  ColdZone,
} from './types';

export type {
  FactionPressure,
  DormantThread,
  ConsequenceEvent,
  ConsequenceNotification,
  FactionPressureZone,
  ConsequenceHighlight,
} from './consequences';

export {
  TILE_SIZE,
  TILE_COLORS,
  TILE_PROPERTIES,
  ENTITY_COLORS,
  MOVEMENT_SPEED,
  PLAYER_RADIUS,
  INTERACTION_RANGE,
  NPC_DETECTION_RANGE,
} from './types';

// Collision utilities
export {
  worldToGrid,
  gridToWorld,
  gridToWorldTopLeft,
  getTileAt,
  isTileWalkable,
  isTileBlockingSight,
  getMovementCost,
  checkCollision,
  hasLineOfSight,
  getWalkableNeighbors,
  manhattanDistance,
  euclideanDistance,
  clampToMapBounds,
} from './collision';

// Map registry
export {
  getMapTemplate,
  getMapsForRegion,
  listMapIds,
  mapExists,
  getDefaultSpawn,
  getSpawnPoint,
  SAFEHOUSE_MAP,
  MARKET_MAP,
  STREET_MAP,
} from './maps';

// Game clock
export {
  useGameClock,
  useTimeEvents,
  formatTime,
  formatTimeShort,
  getTimeOfDay,
  getAmbientLightForTime,
  timeToMinutes,
  minutesToTime,
} from './useGameClock';

export { useConsequences } from './useConsequences';

export type {
  GameTime,
  GameClockState,
  GameClockActions,
  TimeOfDay,
  TimeEvent,
} from './useGameClock';
