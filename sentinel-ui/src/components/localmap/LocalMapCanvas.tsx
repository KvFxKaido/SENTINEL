/**
 * LocalMapCanvas — Tile-based local map renderer (Phase 2)
 * 
 * Renders authored local maps with collision-aware movement.
 * Fixed isometric-style top-down view with tile grid.
 * 
 * Design Constraints:
 * - Movement is free but non-authoritative
 * - Proximity alone never commits
 * - Clear visual distinction between observation and commitment
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import type { 
  LocalMapTemplate, 
  MapObject,
  MapExit,
  Point,
  GridPosition,
} from './types';
import {
  TileType,
  TILE_SIZE,
  TILE_COLORS,
  TILE_PROPERTIES,
  ENTITY_COLORS,
  MOVEMENT_SPEED,
  PLAYER_RADIUS,
  INTERACTION_RANGE,
} from './types';
import {
  checkCollision,
  worldToGrid,
  gridToWorld,
  euclideanDistance,
  clampToMapBounds,
} from './collision';

// ============================================================================
// Types
// ============================================================================

interface LocalMapCanvasProps {
  map: LocalMapTemplate;
  initialPosition?: Point;
  initialFacing?: 'north' | 'south' | 'east' | 'west';
  onExitApproach?: (exit: MapExit) => void;
  onObjectInteract?: (object: MapObject) => void;
  onPositionChange?: (position: Point, gridPos: GridPosition) => void;
  paused?: boolean;
}

interface InteractionPrompt {
  target: MapObject | MapExit;
  type: 'object' | 'exit';
  action: string;
  distance: number;
}

// ============================================================================
// Rendering Helpers
// ============================================================================

function drawTile(
  ctx: CanvasRenderingContext2D,
  col: number,
  row: number,
  tileType: TileType,
  ambientLight: number
) {
  const x = col * TILE_SIZE;
  const y = row * TILE_SIZE;
  
  // Base tile color
  let color = TILE_COLORS[tileType] || TILE_COLORS[TileType.FLOOR];
  
  // Apply ambient light
  ctx.fillStyle = adjustBrightness(color, ambientLight);
  ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
  
  // Tile-specific decorations
  const props = TILE_PROPERTIES[tileType];
  
  // Wall top edge highlight
  if (tileType === TileType.WALL) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.fillRect(x, y, TILE_SIZE, 2);
  }
  
  // Low wall indicator
  if (tileType === TileType.WALL_LOW) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.fillRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);
  }
  
  // Door indicator
  if (tileType === TileType.DOOR || tileType === TileType.DOOR_LOCKED) {
    ctx.strokeStyle = tileType === TileType.DOOR ? '#4a6a4a' : '#6a4a4a';
    ctx.lineWidth = 2;
    ctx.strokeRect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8);
  }
  
  // Exit glow
  if (tileType === TileType.EXIT) {
    const gradient = ctx.createRadialGradient(
      x + TILE_SIZE / 2, y + TILE_SIZE / 2, 0,
      x + TILE_SIZE / 2, y + TILE_SIZE / 2, TILE_SIZE / 2
    );
    gradient.addColorStop(0, 'rgba(63, 185, 80, 0.3)');
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
  }
  
  // Terminal/container icons
  if (tileType === TileType.TERMINAL) {
    ctx.fillStyle = '#3a5a7a';
    ctx.fillRect(x + 8, y + 6, TILE_SIZE - 16, TILE_SIZE - 12);
    ctx.fillStyle = '#5a8aba';
    ctx.fillRect(x + 10, y + 8, TILE_SIZE - 20, TILE_SIZE - 18);
  }
  
  if (tileType === TileType.CONTAINER) {
    ctx.fillStyle = '#5a4a30';
    ctx.fillRect(x + 4, y + 8, TILE_SIZE - 8, TILE_SIZE - 12);
    ctx.strokeStyle = '#7a6a50';
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 4, y + 8, TILE_SIZE - 8, TILE_SIZE - 12);
  }
  
  // Debris scatter
  if (tileType === TileType.DEBRIS) {
    ctx.fillStyle = 'rgba(100, 90, 70, 0.5)';
    for (let i = 0; i < 4; i++) {
      const dx = 4 + Math.random() * (TILE_SIZE - 12);
      const dy = 4 + Math.random() * (TILE_SIZE - 12);
      const size = 2 + Math.random() * 4;
      ctx.fillRect(x + dx, y + dy, size, size);
    }
  }
  
  // Cover indicators
  if (tileType === TileType.COVER_HALF || tileType === TileType.COVER_FULL) {
    ctx.fillStyle = tileType === TileType.COVER_FULL ? '#3a3a4a' : '#2a2a3a';
    ctx.fillRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);
  }
  
  // Grid lines (subtle)
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
  ctx.lineWidth = 1;
  ctx.strokeRect(x, y, TILE_SIZE, TILE_SIZE);
}

function drawPlayer(
  ctx: CanvasRenderingContext2D,
  position: Point,
  facing: 'north' | 'south' | 'east' | 'west'
) {
  const { x, y } = position;
  
  // Glow effect
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, PLAYER_RADIUS * 2);
  gradient.addColorStop(0, 'rgba(86, 212, 221, 0.3)');
  gradient.addColorStop(1, 'transparent');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(x, y, PLAYER_RADIUS * 2, 0, Math.PI * 2);
  ctx.fill();
  
  // Player body
  ctx.fillStyle = ENTITY_COLORS.player;
  ctx.beginPath();
  ctx.arc(x, y, PLAYER_RADIUS, 0, Math.PI * 2);
  ctx.fill();
  
  // Direction indicator
  const angles = {
    north: -Math.PI / 2,
    south: Math.PI / 2,
    east: 0,
    west: Math.PI,
  };
  
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angles[facing]);
  ctx.beginPath();
  ctx.moveTo(PLAYER_RADIUS + 4, 0);
  ctx.lineTo(PLAYER_RADIUS - 3, -4);
  ctx.lineTo(PLAYER_RADIUS - 3, 4);
  ctx.closePath();
  ctx.fillStyle = ENTITY_COLORS.player;
  ctx.fill();
  ctx.restore();
}

function drawObject(
  ctx: CanvasRenderingContext2D,
  obj: MapObject,
  isNearby: boolean,
  isSelected: boolean
) {
  const pos = gridToWorld(obj.position.col, obj.position.row);
  const radius = 10;
  
  // Determine color based on type
  let color = ENTITY_COLORS.prop;
  if (obj.type === 'npc') {
    const npcData = obj.data as { disposition?: string } | undefined;
    const disposition = npcData?.disposition || 'neutral';
    color = ENTITY_COLORS.npc[disposition as keyof typeof ENTITY_COLORS.npc] || ENTITY_COLORS.npc.neutral;
  } else if (obj.type === 'item') {
    color = ENTITY_COLORS.item;
  }
  
  // Nearby highlight
  if (isNearby) {
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, INTERACTION_RANGE, 0, Math.PI * 2);
    ctx.fillStyle = `${color}15`;
    ctx.fill();
  }
  
  // Selection ring
  if (isSelected) {
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius + 6, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  
  // Object body
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  
  // NPC facing indicator
  if (obj.type === 'npc' && obj.data) {
    const npcData = obj.data as { facing?: string };
    if (npcData.facing) {
      const angles = {
        north: -Math.PI / 2,
        south: Math.PI / 2,
        east: 0,
        west: Math.PI,
      };
      const angle = angles[npcData.facing as keyof typeof angles] || 0;
      
      ctx.save();
      ctx.translate(pos.x, pos.y);
      ctx.rotate(angle);
      ctx.beginPath();
      ctx.moveTo(radius + 3, 0);
      ctx.lineTo(radius - 2, -3);
      ctx.lineTo(radius - 2, 3);
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();
      ctx.restore();
    }
  }
  
  // Label (when nearby)
  if (isNearby || isSelected) {
    ctx.fillStyle = color;
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(obj.name, pos.x, pos.y - radius - 6);
  }
}

function drawExit(
  ctx: CanvasRenderingContext2D,
  exit: MapExit,
  isNearby: boolean
) {
  const pos = gridToWorld(exit.position.col, exit.position.row);
  const color = exit.locked ? ENTITY_COLORS.exit.locked : ENTITY_COLORS.exit.open;
  
  // Exit glow when nearby
  if (isNearby && !exit.locked) {
    const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, TILE_SIZE);
    gradient.addColorStop(0, `${color}40`);
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.fillRect(pos.x - TILE_SIZE, pos.y - TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2);
  }
  
  // Direction arrow
  const arrows = {
    north: '↑',
    south: '↓',
    east: '→',
    west: '←',
    up: '⬆',
    down: '⬇',
  };
  
  ctx.fillStyle = color;
  ctx.font = '16px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(arrows[exit.direction], pos.x, pos.y);
  
  // Label when nearby
  if (isNearby) {
    ctx.fillStyle = color;
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(exit.label, pos.x, pos.y + 20);
    
    if (exit.locked && exit.lockReason) {
      ctx.fillStyle = ENTITY_COLORS.exit.locked;
      ctx.fillText(`[${exit.lockReason}]`, pos.x, pos.y + 32);
    }
  }
}

function drawInteractionPrompt(
  ctx: CanvasRenderingContext2D,
  prompt: InteractionPrompt,
  canvasWidth: number
) {
  const target = prompt.target;
  const pos = 'position' in target 
    ? gridToWorld(target.position.col, target.position.row)
    : { x: 0, y: 0 };
  
  const text = `[E] ${prompt.action}`;
  ctx.font = '11px "JetBrains Mono", monospace';
  const textWidth = ctx.measureText(text).width;
  const padding = 6;
  const boxWidth = textWidth + padding * 2;
  const boxHeight = 20;
  
  let boxX = pos.x - boxWidth / 2;
  const boxY = pos.y + 28;
  
  // Keep on screen
  if (boxX < 5) boxX = 5;
  if (boxX + boxWidth > canvasWidth - 5) boxX = canvasWidth - boxWidth - 5;
  
  // Background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
  ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
  
  // Border
  ctx.strokeStyle = 'rgba(88, 166, 255, 0.8)';
  ctx.lineWidth = 1;
  ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);
  
  // Text
  ctx.fillStyle = 'rgba(88, 166, 255, 0.95)';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, boxX + boxWidth / 2, boxY + boxHeight / 2);
}

function drawMapInfo(
  ctx: CanvasRenderingContext2D,
  mapName: string,
  atmosphere: string,
  width: number
) {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.fillRect(0, 0, width, 28);
  
  // Map name
  ctx.fillStyle = ENTITY_COLORS.player;
  ctx.font = '11px "JetBrains Mono", monospace';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(mapName.toUpperCase(), 10, 14);
  
  // Atmosphere indicator
  const atmosphereColors = {
    safe: '#3fb950',
    neutral: '#8b949e',
    tense: '#d29922',
    hostile: '#f85149',
  };
  ctx.fillStyle = atmosphereColors[atmosphere as keyof typeof atmosphereColors] || atmosphereColors.neutral;
  ctx.textAlign = 'right';
  ctx.fillText(`[${atmosphere.toUpperCase()}]`, width - 10, 14);
}

function adjustBrightness(hex: string, factor: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  
  const nr = Math.round(r * factor);
  const ng = Math.round(g * factor);
  const nb = Math.round(b * factor);
  
  return `rgb(${nr}, ${ng}, ${nb})`;
}

// ============================================================================
// Component
// ============================================================================

export function LocalMapCanvas({
  map,
  initialPosition,
  initialFacing = 'south',
  onExitApproach,
  onObjectInteract,
  onPositionChange,
  paused = false,
}: LocalMapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const keysPressed = useRef<Set<string>>(new Set());
  
  // Calculate initial position from default spawn if not provided
  const defaultSpawn = map.spawnPoints.find(sp => sp.isDefault) || map.spawnPoints[0];
  const startPos = initialPosition || (defaultSpawn 
    ? gridToWorld(defaultSpawn.position.col, defaultSpawn.position.row)
    : { x: map.width * TILE_SIZE / 2, y: map.height * TILE_SIZE / 2 });
  
  const [playerPos, setPlayerPos] = useState<Point>(startPos);
  const [playerFacing, setPlayerFacing] = useState<'north' | 'south' | 'east' | 'west'>(
    initialFacing || (defaultSpawn?.facing as typeof initialFacing) || 'south'
  );
  const [nearbyObjects, setNearbyObjects] = useState<MapObject[]>([]);
  const [nearbyExits, setNearbyExits] = useState<MapExit[]>([]);
  const [activePrompt, setActivePrompt] = useState<InteractionPrompt | null>(null);
  
  const canvasWidth = map.width * TILE_SIZE;
  const canvasHeight = map.height * TILE_SIZE;
  
  // Find nearby interactables
  useEffect(() => {
    const nearby: MapObject[] = [];
    for (const obj of map.objects) {
      const objPos = gridToWorld(obj.position.col, obj.position.row);
      const dist = euclideanDistance(playerPos, objPos);
      if (dist < INTERACTION_RANGE) {
        nearby.push(obj);
      }
    }
    setNearbyObjects(nearby);
    
    const nearExits: MapExit[] = [];
    for (const exit of map.exits) {
      const exitPos = gridToWorld(exit.position.col, exit.position.row);
      const dist = euclideanDistance(playerPos, exitPos);
      if (dist < INTERACTION_RANGE) {
        nearExits.push(exit);
        if (!exit.locked) {
          onExitApproach?.(exit);
        }
      }
    }
    setNearbyExits(nearExits);
    
    // Set active prompt to closest interactable
    let closestDist = INTERACTION_RANGE;
    let closestPrompt: InteractionPrompt | null = null;
    
    for (const obj of nearby) {
      const objPos = gridToWorld(obj.position.col, obj.position.row);
      const dist = euclideanDistance(playerPos, objPos);
      if (dist < closestDist) {
        closestDist = dist;
        closestPrompt = {
          target: obj,
          type: 'object',
          action: getObjectAction(obj),
          distance: dist,
        };
      }
    }
    
    for (const exit of nearExits) {
      const exitPos = gridToWorld(exit.position.col, exit.position.row);
      const dist = euclideanDistance(playerPos, exitPos);
      if (dist < closestDist) {
        closestDist = dist;
        closestPrompt = {
          target: exit,
          type: 'exit',
          action: exit.locked ? `Locked: ${exit.lockReason}` : `Go to ${exit.label}`,
          distance: dist,
        };
      }
    }
    
    setActivePrompt(closestPrompt);
  }, [playerPos, map.objects, map.exits, onExitApproach]);
  
  // Notify position changes
  useEffect(() => {
    const gridPos = worldToGrid(playerPos.x, playerPos.y);
    onPositionChange?.(playerPos, gridPos);
  }, [playerPos, onPositionChange]);
  
  // Movement loop
  useEffect(() => {
    if (paused) return;
    
    let animationId: number;
    
    function update() {
      const keys = keysPressed.current;
      let vx = 0;
      let vy = 0;
      let newFacing: typeof playerFacing | null = null;
      
      if (keys.has('w') || keys.has('arrowup')) { vy = -MOVEMENT_SPEED; newFacing = 'north'; }
      if (keys.has('s') || keys.has('arrowdown')) { vy = MOVEMENT_SPEED; newFacing = 'south'; }
      if (keys.has('a') || keys.has('arrowleft')) { vx = -MOVEMENT_SPEED; newFacing = 'west'; }
      if (keys.has('d') || keys.has('arrowright')) { vx = MOVEMENT_SPEED; newFacing = 'east'; }
      
      // Diagonal movement normalization
      if (vx !== 0 && vy !== 0) {
        const factor = 1 / Math.sqrt(2);
        vx *= factor;
        vy *= factor;
      }
      
      if (newFacing) {
        setPlayerFacing(newFacing);
      }
      
      if (vx !== 0 || vy !== 0) {
        setPlayerPos(prev => {
          const targetPos = { x: prev.x + vx, y: prev.y + vy };
          const clamped = clampToMapBounds(map, targetPos, PLAYER_RADIUS);
          const collision = checkCollision(map, prev, clamped, PLAYER_RADIUS);
          return collision.newPosition;
        });
      }
      
      animationId = requestAnimationFrame(update);
    }
    
    animationId = requestAnimationFrame(update);
    return () => cancelAnimationFrame(animationId);
  }, [map, paused]);
  
  // Keyboard handlers
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const key = e.key.toLowerCase();
      keysPressed.current.add(key);
      
      // Interaction
      if (key === 'e' && activePrompt && !paused) {
        if (activePrompt.type === 'object') {
          onObjectInteract?.(activePrompt.target as MapObject);
        } else if (activePrompt.type === 'exit') {
          const exit = activePrompt.target as MapExit;
          if (!exit.locked) {
            onExitApproach?.(exit);
          }
        }
      }
    }
    
    function handleKeyUp(e: KeyboardEvent) {
      keysPressed.current.delete(e.key.toLowerCase());
    }
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [activePrompt, paused, onObjectInteract, onExitApproach]);
  
  // Render
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // Draw tiles
    for (let row = 0; row < map.height; row++) {
      for (let col = 0; col < map.width; col++) {
        drawTile(ctx, col, row, map.tiles[row][col], map.ambientLight);
      }
    }
    
    // Draw exits
    for (const exit of map.exits) {
      const isNearby = nearbyExits.includes(exit);
      drawExit(ctx, exit, isNearby);
    }
    
    // Draw objects
    for (const obj of map.objects) {
      const isNearby = nearbyObjects.includes(obj);
      const isSelected = activePrompt?.type === 'object' && 
        (activePrompt.target as MapObject).id === obj.id;
      drawObject(ctx, obj, isNearby, isSelected);
    }
    
    // Draw player
    drawPlayer(ctx, playerPos, playerFacing);
    
    // Draw interaction prompt
    if (activePrompt) {
      drawInteractionPrompt(ctx, activePrompt, canvasWidth);
    }
    
    // Draw map info overlay
    drawMapInfo(ctx, map.name, map.atmosphere, canvasWidth);
    
  }, [map, playerPos, playerFacing, nearbyObjects, nearbyExits, activePrompt, canvasWidth, canvasHeight]);
  
  return (
    <canvas
      ref={canvasRef}
      width={canvasWidth}
      height={canvasHeight}
      style={{ 
        display: 'block', 
        background: '#000',
        imageRendering: 'pixelated',
      }}
      tabIndex={0}
    />
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getObjectAction(obj: MapObject): string {
  switch (obj.type) {
    case 'npc':
      return `Talk to ${obj.name}`;
    case 'item':
      return `Pick up ${obj.name}`;
    case 'prop':
      const propData = obj.data as { interactable?: boolean; propType?: string };
      if (!propData?.interactable) return `Examine ${obj.name}`;
      if (propData.propType === 'terminal') return `Use ${obj.name}`;
      if (propData.propType === 'container') return `Open ${obj.name}`;
      return `Interact with ${obj.name}`;
    case 'trigger':
      return 'Investigate';
    default:
      return 'Interact';
  }
}
