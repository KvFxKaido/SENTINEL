/**
 * Collision Detection System (Phase 2)
 * 
 * Handles tile-based collision with smooth movement.
 * Uses swept AABB for accurate collision response.
 */

import type { Point, GridPosition, LocalMapTemplate, TileType } from './types';
import { TILE_PROPERTIES, TILE_SIZE, PLAYER_RADIUS } from './types';

// ============================================================================
// Coordinate Conversion
// ============================================================================

export function worldToGrid(x: number, y: number): GridPosition {
  return {
    col: Math.floor(x / TILE_SIZE),
    row: Math.floor(y / TILE_SIZE),
  };
}

export function gridToWorld(col: number, row: number): Point {
  return {
    x: col * TILE_SIZE + TILE_SIZE / 2,
    y: row * TILE_SIZE + TILE_SIZE / 2,
  };
}

export function gridToWorldTopLeft(col: number, row: number): Point {
  return {
    x: col * TILE_SIZE,
    y: row * TILE_SIZE,
  };
}

// ============================================================================
// Tile Queries
// ============================================================================

export function getTileAt(map: LocalMapTemplate, col: number, row: number): TileType | null {
  if (row < 0 || row >= map.height || col < 0 || col >= map.width) {
    return null; // Out of bounds treated as wall
  }
  return map.tiles[row][col];
}

export function isTileWalkable(map: LocalMapTemplate, col: number, row: number): boolean {
  const tile = getTileAt(map, col, row);
  if (tile === null) return false;
  return TILE_PROPERTIES[tile].walkable;
}

export function isTileBlockingSight(map: LocalMapTemplate, col: number, row: number): boolean {
  const tile = getTileAt(map, col, row);
  if (tile === null) return true;
  return TILE_PROPERTIES[tile].blocksSight;
}

export function getMovementCost(map: LocalMapTemplate, col: number, row: number): number {
  const tile = getTileAt(map, col, row);
  if (tile === null) return 0;
  return TILE_PROPERTIES[tile].movementCost;
}

// ============================================================================
// Collision Detection
// ============================================================================

interface CollisionResult {
  collided: boolean;
  newPosition: Point;
  collidedTiles: GridPosition[];
  slideX: boolean;
  slideY: boolean;
}

/**
 * Check collision and return adjusted position.
 * Uses swept collision with wall sliding.
 */
export function checkCollision(
  map: LocalMapTemplate,
  currentPos: Point,
  targetPos: Point,
  radius: number = PLAYER_RADIUS
): CollisionResult {
  const result: CollisionResult = {
    collided: false,
    newPosition: { ...targetPos },
    collidedTiles: [],
    slideX: false,
    slideY: false,
  };

  // Get all tiles the entity could potentially collide with
  const minCol = Math.floor((Math.min(currentPos.x, targetPos.x) - radius) / TILE_SIZE);
  const maxCol = Math.floor((Math.max(currentPos.x, targetPos.x) + radius) / TILE_SIZE);
  const minRow = Math.floor((Math.min(currentPos.y, targetPos.y) - radius) / TILE_SIZE);
  const maxRow = Math.floor((Math.max(currentPos.y, targetPos.y) + radius) / TILE_SIZE);

  // Check each potentially colliding tile
  for (let row = minRow; row <= maxRow; row++) {
    for (let col = minCol; col <= maxCol; col++) {
      if (!isTileWalkable(map, col, row)) {
        // Check circle-AABB collision
        const tileLeft = col * TILE_SIZE;
        const tileRight = tileLeft + TILE_SIZE;
        const tileTop = row * TILE_SIZE;
        const tileBottom = tileTop + TILE_SIZE;

        if (circleAABBCollision(targetPos.x, targetPos.y, radius, tileLeft, tileTop, tileRight, tileBottom)) {
          result.collided = true;
          result.collidedTiles.push({ col, row });
        }
      }
    }
  }

  // If no collision, return target position
  if (!result.collided) {
    return result;
  }

  // Try sliding along walls
  // First try moving only in X
  const slideXPos = { x: targetPos.x, y: currentPos.y };
  let canSlideX = true;
  for (const tile of result.collidedTiles) {
    const tileLeft = tile.col * TILE_SIZE;
    const tileRight = tileLeft + TILE_SIZE;
    const tileTop = tile.row * TILE_SIZE;
    const tileBottom = tileTop + TILE_SIZE;
    if (circleAABBCollision(slideXPos.x, slideXPos.y, radius, tileLeft, tileTop, tileRight, tileBottom)) {
      canSlideX = false;
      break;
    }
  }

  // Then try moving only in Y
  const slideYPos = { x: currentPos.x, y: targetPos.y };
  let canSlideY = true;
  for (const tile of result.collidedTiles) {
    const tileLeft = tile.col * TILE_SIZE;
    const tileRight = tileLeft + TILE_SIZE;
    const tileTop = tile.row * TILE_SIZE;
    const tileBottom = tileTop + TILE_SIZE;
    if (circleAABBCollision(slideYPos.x, slideYPos.y, radius, tileLeft, tileTop, tileRight, tileBottom)) {
      canSlideY = false;
      break;
    }
  }

  // Determine best slide direction
  if (canSlideX && !canSlideY) {
    result.newPosition = slideXPos;
    result.slideX = true;
  } else if (canSlideY && !canSlideX) {
    result.newPosition = slideYPos;
    result.slideY = true;
  } else if (canSlideX && canSlideY) {
    // Both work, pick the one with more movement
    const dxSlide = Math.abs(slideXPos.x - currentPos.x);
    const dySlide = Math.abs(slideYPos.y - currentPos.y);
    if (dxSlide > dySlide) {
      result.newPosition = slideXPos;
      result.slideX = true;
    } else {
      result.newPosition = slideYPos;
      result.slideY = true;
    }
  } else {
    // Can't slide, stay in place
    result.newPosition = currentPos;
  }

  return result;
}

/**
 * Circle-AABB collision test
 */
function circleAABBCollision(
  cx: number, cy: number, radius: number,
  left: number, top: number, right: number, bottom: number
): boolean {
  // Find closest point on AABB to circle center
  const closestX = Math.max(left, Math.min(cx, right));
  const closestY = Math.max(top, Math.min(cy, bottom));

  // Calculate distance from circle center to closest point
  const dx = cx - closestX;
  const dy = cy - closestY;
  const distSquared = dx * dx + dy * dy;

  return distSquared < radius * radius;
}

// ============================================================================
// Line of Sight
// ============================================================================

/**
 * Check if there's clear line of sight between two points.
 * Uses Bresenham's line algorithm on the tile grid.
 */
export function hasLineOfSight(
  map: LocalMapTemplate,
  from: Point,
  to: Point
): boolean {
  const fromGrid = worldToGrid(from.x, from.y);
  const toGrid = worldToGrid(to.x, to.y);

  // Bresenham's line algorithm
  let x0 = fromGrid.col;
  let y0 = fromGrid.row;
  const x1 = toGrid.col;
  const y1 = toGrid.row;

  const dx = Math.abs(x1 - x0);
  const dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;

  while (true) {
    // Skip start and end tiles
    if ((x0 !== fromGrid.col || y0 !== fromGrid.row) && 
        (x0 !== toGrid.col || y0 !== toGrid.row)) {
      if (isTileBlockingSight(map, x0, y0)) {
        return false;
      }
    }

    if (x0 === x1 && y0 === y1) break;

    const e2 = 2 * err;
    if (e2 > -dy) {
      err -= dy;
      x0 += sx;
    }
    if (e2 < dx) {
      err += dx;
      y0 += sy;
    }
  }

  return true;
}

// ============================================================================
// Pathfinding Helpers
// ============================================================================

/**
 * Get walkable neighbors for pathfinding.
 */
export function getWalkableNeighbors(
  map: LocalMapTemplate,
  pos: GridPosition
): GridPosition[] {
  const neighbors: GridPosition[] = [];
  const directions = [
    { col: 0, row: -1 },  // North
    { col: 1, row: 0 },   // East
    { col: 0, row: 1 },   // South
    { col: -1, row: 0 },  // West
  ];

  for (const dir of directions) {
    const newCol = pos.col + dir.col;
    const newRow = pos.row + dir.row;
    if (isTileWalkable(map, newCol, newRow)) {
      neighbors.push({ col: newCol, row: newRow });
    }
  }

  return neighbors;
}

/**
 * Calculate Manhattan distance between two grid positions.
 */
export function manhattanDistance(a: GridPosition, b: GridPosition): number {
  return Math.abs(a.col - b.col) + Math.abs(a.row - b.row);
}

/**
 * Calculate Euclidean distance between two points.
 */
export function euclideanDistance(a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  return Math.sqrt(dx * dx + dy * dy);
}

// ============================================================================
// Bounds Checking
// ============================================================================

/**
 * Clamp position to map bounds.
 */
export function clampToMapBounds(
  map: LocalMapTemplate,
  pos: Point,
  radius: number = PLAYER_RADIUS
): Point {
  const maxX = map.width * TILE_SIZE - radius;
  const maxY = map.height * TILE_SIZE - radius;

  return {
    x: Math.max(radius, Math.min(pos.x, maxX)),
    y: Math.max(radius, Math.min(pos.y, maxY)),
  };
}
