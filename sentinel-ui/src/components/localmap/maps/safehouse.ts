/**
 * Safehouse Local Map
 * 
 * The player's home base. Small, intentional space.
 * Safe atmosphere - no patrols, no tension.
 */

import { TileType, type LocalMapTemplate } from '../types';

const _ = TileType.FLOOR;
const W = TileType.WALL;
const w = TileType.WALL_LOW;
const D = TileType.DOOR;
const X = TileType.EXIT;
const T = TileType.TERMINAL;
const C = TileType.CONTAINER;
const d = TileType.DEBRIS;

export const SAFEHOUSE_MAP: LocalMapTemplate = {
  id: 'safehouse_main',
  name: 'Safehouse',
  regionId: 'rust_corridor',
  description: 'A converted storage unit. Cramped but secure.',
  
  width: 16,
  height: 12,
  tileSize: 32,
  
  // 16x12 tile grid
  tiles: [
    [W, W, W, W, W, W, W, W, W, W, W, W, W, W, W, W],
    [W, _, _, _, _, _, W, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, W, _, _, _, _, _, _, _, _, W],
    [W, _, _, T, _, _, D, _, _, _, _, _, C, _, _, W],
    [W, _, _, _, _, _, W, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, W, W, W, D, W, W, W, W, W, W],
    [W, W, W, D, W, W, W, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, _, _, _, _, _, _, _, _, d, _, _, _, _, _, W],
    [W, _, C, _, _, _, _, _, _, _, _, _, _, C, _, W],
    [W, _, _, _, _, _, _, _, _, _, _, _, _, _, _, W],
    [W, W, W, W, W, W, W, W, X, W, W, W, W, W, W, W],
  ],
  
  objects: [
    {
      id: 'terminal_main',
      type: 'prop',
      position: { col: 3, row: 3 },
      name: 'Personal Terminal',
      data: {
        propType: 'terminal',
        interactable: true,
        state: 'idle',
      },
    },
    {
      id: 'stash_weapons',
      type: 'prop',
      position: { col: 12, row: 3 },
      name: 'Weapon Stash',
      data: {
        propType: 'container',
        interactable: true,
        state: 'closed',
      },
    },
    {
      id: 'stash_supplies',
      type: 'prop',
      position: { col: 2, row: 9 },
      name: 'Supply Crate',
      data: {
        propType: 'container',
        interactable: true,
        state: 'closed',
      },
    },
    {
      id: 'stash_misc',
      type: 'prop',
      position: { col: 13, row: 9 },
      name: 'Misc Storage',
      data: {
        propType: 'container',
        interactable: true,
        state: 'closed',
      },
    },
  ],
  
  exits: [
    {
      id: 'exit_street',
      position: { col: 8, row: 11 },
      direction: 'south',
      targetMap: 'rust_corridor_street',
      targetSpawn: 'from_safehouse',
      label: 'Exit to Street',
      locked: false,
    },
  ],
  
  spawnPoints: [
    {
      id: 'default',
      position: { col: 8, row: 8 },
      facing: 'north',
      isDefault: true,
    },
    {
      id: 'from_street',
      position: { col: 8, row: 10 },
      facing: 'north',
      isDefault: false,
    },
  ],
  
  ambientLight: 0.6,
  atmosphere: 'safe',
  
  author: 'SENTINEL',
  version: 1,
};
