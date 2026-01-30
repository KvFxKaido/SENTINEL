/**
 * Rust Corridor Street Local Map
 * 
 * Hub connecting various locations. Open but exposed.
 * Neutral atmosphere but with patrol presence.
 */

import { TileType, NPCBehaviorState, type LocalMapTemplate } from '../types';

const _ = TileType.FLOOR;
const W = TileType.WALL;
const w = TileType.WALL_LOW;
const D = TileType.DOOR;
const X = TileType.EXIT;
const d = TileType.DEBRIS;
const H = TileType.COVER_HALF;
const F = TileType.COVER_FULL;

export const STREET_MAP: LocalMapTemplate = {
  id: 'rust_corridor_street',
  name: 'Rust Corridor - Main Street',
  regionId: 'rust_corridor',
  description: 'The main thoroughfare. Exposed but well-traveled.',
  
  width: 24,
  height: 20,
  tileSize: 32,
  
  // 24x20 tile grid - vertical street with side alleys
  tiles: [
    [W, W, W, W, W, W, W, W, X, W, W, W, W, W, X, W, W, W, W, W, W, W, W, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, d, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, d, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, W, W, W, D, W, _, _, _, _, _, _, _, _, _, _, _, _, W, D, W, W, W, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, F, _, _, _, _, _, _, F, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, d, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, F, _, _, _, _, _, _, F, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, W, W, W, D, W, _, _, _, _, _, _, _, _, _, _, _, _, W, D, W, W, W, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, d, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, d, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, W, W, W, W, W, W, W, X, W, W, W, W, W, X, W, W, W, W, W, W, W, W, W],
  ],
  
  objects: [
    // Patrol NPC
    {
      id: 'patrol_lattice',
      type: 'npc',
      position: { col: 12, row: 5 },
      name: 'Lattice Patrol',
      data: {
        npcId: 'lattice_patrol_1',
        faction: 'steel_syndicate', // Remapped to steel_syndicate for behavior testing
        disposition: 'neutral',
        patrolRoute: [
          { col: 12, row: 5 },
          { col: 12, row: 14 },
          { col: 8, row: 14 },
          { col: 8, row: 5 },
        ],
      },
    },
    {
      id: 'patrol_ember',
      type: 'npc',
      position: { col: 16, row: 16 },
      name: 'Ember Scavenger',
      data: {
        npcId: 'ember_scavenger_1',
        faction: 'ember_colonies',
        disposition: 'wary',
        patrolRoute: [
          { col: 16, row: 16 },
          { col: 20, row: 16 },
          { col: 20, row: 12 },
          { col: 16, row: 12 },
        ],
      },
    },
    // Street vendor
    {
      id: 'street_vendor',
      type: 'npc',
      position: { col: 3, row: 9 },
      name: 'Street Vendor',
      data: {
        npcId: 'street_vendor_1',
        faction: 'wanderers',
        disposition: 'warm',
        facing: 'east',
      },
    },
    // Bystander
    {
      id: 'bystander_1',
      type: 'npc',
      position: { col: 20, row: 9 },
      name: 'Nervous Civilian',
      data: {
        npcId: 'civilian_1',
        faction: null,
        disposition: 'wary',
        behaviorState: NPCBehaviorState.ALERT,
        fleeOnApproach: true,
      },
    },
  ],
  
  exits: [
    // North exits
    {
      id: 'exit_north_market',
      position: { col: 8, row: 0 },
      direction: 'north',
      targetMap: 'rust_corridor_market',
      targetSpawn: 'from_street',
      label: 'Black Market',
      locked: false,
    },
    {
      id: 'exit_north_checkpoint',
      position: { col: 14, row: 0 },
      direction: 'north',
      targetMap: 'lattice_checkpoint',
      targetSpawn: 'from_street',
      label: 'Lattice Checkpoint',
      locked: false,
    },
    // South exits
    {
      id: 'exit_south_safehouse',
      position: { col: 8, row: 19 },
      direction: 'south',
      targetMap: 'safehouse_main',
      targetSpawn: 'from_street',
      label: 'Safehouse',
      locked: false,
    },
    {
      id: 'exit_south_outskirts',
      position: { col: 14, row: 19 },
      direction: 'south',
      targetMap: 'rust_corridor_outskirts',
      targetSpawn: 'from_street',
      label: 'Outskirts',
      locked: false,
    },
    // Side alleys (via doors)
    {
      id: 'exit_west_alley',
      position: { col: 4, row: 5 },
      direction: 'west',
      targetMap: 'rust_corridor_alley_west',
      targetSpawn: 'from_street',
      label: 'West Alley',
      locked: false,
    },
    {
      id: 'exit_east_alley',
      position: { col: 19, row: 5 },
      direction: 'east',
      targetMap: 'rust_corridor_alley_east',
      targetSpawn: 'from_street',
      label: 'East Alley',
      locked: false,
    },
    {
      id: 'exit_west_backstreet',
      position: { col: 4, row: 13 },
      direction: 'west',
      targetMap: 'rust_corridor_backstreet',
      targetSpawn: 'from_main',
      label: 'Backstreet',
      locked: true,
      lockReason: 'Blocked by debris',
    },
    {
      id: 'exit_east_warehouse',
      position: { col: 19, row: 13 },
      direction: 'east',
      targetMap: 'rust_corridor_warehouse',
      targetSpawn: 'from_street',
      label: 'Warehouse',
      locked: true,
      lockReason: 'Requires key',
      requiresKey: 'warehouse_key',
    },
  ],
  
  spawnPoints: [
    {
      id: 'default',
      position: { col: 11, row: 10 },
      facing: 'north',
      isDefault: true,
    },
    {
      id: 'from_safehouse',
      position: { col: 8, row: 18 },
      facing: 'north',
      isDefault: false,
    },
    {
      id: 'from_market',
      position: { col: 8, row: 1 },
      facing: 'south',
      isDefault: false,
    },
    {
      id: 'from_checkpoint',
      position: { col: 14, row: 1 },
      facing: 'south',
      isDefault: false,
    },
    {
      id: 'from_outskirts',
      position: { col: 14, row: 18 },
      facing: 'north',
      isDefault: false,
    },
  ],
  
  ambientLight: 0.7,
  atmosphere: 'neutral',
  
  author: 'SENTINEL',
  version: 1,
};
