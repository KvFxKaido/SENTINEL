/**
 * Local Map Registry
 * 
 * Central registry for all local maps.
 * Maps are loaded by ID.
 */

import type { LocalMapTemplate } from '../types';
import { SAFEHOUSE_MAP } from './safehouse';
import { MARKET_MAP } from './market';
import { STREET_MAP } from './street';

// Map registry
const MAP_REGISTRY: Record<string, LocalMapTemplate> = {
  [SAFEHOUSE_MAP.id]: SAFEHOUSE_MAP,
  [MARKET_MAP.id]: MARKET_MAP,
  [STREET_MAP.id]: STREET_MAP,
};

/**
 * Get a map template by ID.
 */
export function getMapTemplate(mapId: string): LocalMapTemplate | null {
  return MAP_REGISTRY[mapId] || null;
}

/**
 * Get all maps for a region.
 */
export function getMapsForRegion(regionId: string): LocalMapTemplate[] {
  return Object.values(MAP_REGISTRY).filter(map => map.regionId === regionId);
}

/**
 * List all available map IDs.
 */
export function listMapIds(): string[] {
  return Object.keys(MAP_REGISTRY);
}

/**
 * Check if a map exists.
 */
export function mapExists(mapId: string): boolean {
  return mapId in MAP_REGISTRY;
}

/**
 * Get the default spawn point for a map.
 */
export function getDefaultSpawn(mapId: string): { col: number; row: number; facing: string } | null {
  const map = getMapTemplate(mapId);
  if (!map) return null;
  
  const defaultSpawn = map.spawnPoints.find(sp => sp.isDefault);
  if (defaultSpawn) {
    return {
      col: defaultSpawn.position.col,
      row: defaultSpawn.position.row,
      facing: defaultSpawn.facing,
    };
  }
  
  // Fallback to first spawn point
  if (map.spawnPoints.length > 0) {
    const sp = map.spawnPoints[0];
    return {
      col: sp.position.col,
      row: sp.position.row,
      facing: sp.facing,
    };
  }
  
  return null;
}

/**
 * Get a specific spawn point.
 */
export function getSpawnPoint(mapId: string, spawnId: string): { col: number; row: number; facing: string } | null {
  const map = getMapTemplate(mapId);
  if (!map) return null;
  
  const spawn = map.spawnPoints.find(sp => sp.id === spawnId);
  if (spawn) {
    return {
      col: spawn.position.col,
      row: spawn.position.row,
      facing: spawn.facing,
    };
  }
  
  return getDefaultSpawn(mapId);
}

// Export individual maps for direct access
export { SAFEHOUSE_MAP, MARKET_MAP, STREET_MAP };
