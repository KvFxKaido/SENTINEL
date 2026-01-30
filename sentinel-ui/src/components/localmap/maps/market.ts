/**
 * Black Market Local Map
 * 
 * Trading post in the Rust Corridor. Neutral ground.
 * Tense atmosphere - factions present but not hostile.
 */

import { TileType, NPCBehaviorState, type LocalMapTemplate } from '../types';

const _ = TileType.FLOOR;
const W = TileType.WALL;
const w = TileType.WALL_LOW;  // Counter/stall
const D = TileType.DOOR;
const X = TileType.EXIT;
const T = TileType.TERMINAL;
const C = TileType.CONTAINER;
const d = TileType.DEBRIS;
const H = TileType.COVER_HALF;  // Market stalls

export const MARKET_MAP: LocalMapTemplate = {
  id: 'rust_corridor_market',
  name: 'Black Market',
  regionId: 'rust_corridor',
  description: 'An underground trading post. Everyone\'s welcome, no one\'s safe.',
  
  width: 20,
  height: 16,
  tileSize: 32,
  
  // 20x16 tile grid
  tiles: [
    [W, W, W, W, W, W, W, W, W, W, W, W, W, W, W, W, W, W, W, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, w, w, _, _, _, w, w, _, _, w, w, _, _, _, w, w, _, W],
    [W, _, w, w, _, _, _, w, w, _, _, w, w, _, _, _, w, w, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, d, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, _, _, _, H, _, _, _, _, _, _, _, _, H, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, w, w, _, _, _, w, w, _, _, w, w, _, _, _, w, w, _, W],
    [W, _, w, w, _, _, _, w, w, _, _, w, w, _, _, _, w, w, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, W, W, W, W, W, W, W, W, X, W, W, W, W, W, W, W, W, W, W],
  ],
  
  objects: [
    // Vendor stalls
    {
      id: 'vendor_weapons',
      type: 'npc',
      position: { col: 3, row: 2 },
      name: 'Arms Dealer',
      data: {
        npcId: 'vendor_arms',
        faction: 'steel_syndicate',
        disposition: 'neutral',
        facing: 'south',
      },
    },
    {
      id: 'vendor_tech',
      type: 'npc',
      position: { col: 8, row: 2 },
      name: 'Tech Broker',
      data: {
        npcId: 'vendor_tech',
        faction: 'lattice',
        disposition: 'neutral',
        facing: 'south',
      },
    },
    {
      id: 'vendor_info',
      type: 'npc',
      position: { col: 12, row: 2 },
      name: 'Information Broker',
      data: {
        npcId: 'vendor_info',
        faction: 'nexus',
        disposition: 'wary',
        facing: 'south',
        behaviorState: NPCBehaviorState.UNAVAILABLE,
      },
    },
    {
      id: 'vendor_supplies',
      type: 'npc',
      position: { col: 17, row: 2 },
      name: 'General Trader',
      data: {
        npcId: 'vendor_general',
        faction: 'wanderers',
        disposition: 'warm',
        facing: 'south',
      },
    },
    // Loitering NPCs
    {
      id: 'patron_1',
      type: 'npc',
      position: { col: 6, row: 7 },
      name: 'Hooded Figure',
      data: {
        npcId: 'market_patron_1',
        faction: null,
        disposition: 'neutral',
        patrolRoute: [
          { col: 6, row: 7 },
          { col: 6, row: 9 },
          { col: 10, row: 9 },
          { col: 10, row: 7 },
        ],
      },
    },
    {
      id: 'patron_2',
      type: 'npc',
      position: { col: 14, row: 11 },
      name: 'Scarred Veteran',
      data: {
        npcId: 'market_patron_2',
        faction: 'ember_colonies',
        disposition: 'wary',
      },
    },
    {
      id: 'guard_1',
      type: 'npc',
      position: { col: 9, row: 14 },
      name: 'Market Guard',
      data: {
        npcId: 'market_guard',
        faction: 'steel_syndicate',
        disposition: 'neutral',
        facing: 'north',
        patrolRoute: [
          { col: 9, row: 14 },
          { col: 9, row: 6 },
          { col: 14, row: 6 },
          { col: 14, row: 14 },
        ],
      },
    },
  ],
  
  exits: [
    {
      id: 'exit_street',
      position: { col: 9, row: 15 },
      direction: 'south',
      targetMap: 'rust_corridor_street',
      targetSpawn: 'from_market',
      label: 'Exit to Street',
      locked: false,
    },
  ],
  
  spawnPoints: [
    {
      id: 'default',
      position: { col: 9, row: 13 },
      facing: 'north',
      isDefault: true,
    },
    {
      id: 'from_street',
      position: { col: 9, row: 14 },
      facing: 'north',
      isDefault: false,
    },
  ],
  
  ambientLight: 0.4,
  atmosphere: 'tense',

  coldZones: [
    {
      id: 'market_center_cold',
      name: 'Market Center',
      bounds: { col: 6, row: 6, width: 8, height: 5 },
      suppressPrompts: true,
      suppressDialogue: true,
    },
  ],
  
  author: 'SENTINEL',
  version: 1,
};
