import { useRef, useEffect, useState, useCallback, type MouseEvent } from 'react';
import type {
  LocalMapTemplate,
  MapObject,
  MapExit,
  Point,
  GridPosition,
  NPCObjectData,
} from './types';
import {
  TileType,
  NPCBehaviorState,
  TILE_SIZE,
  TILE_COLORS,
  TILE_PROPERTIES,
  ENTITY_COLORS,
  MOVEMENT_SPEED,
  PLAYER_RADIUS,
  INTERACTION_RANGE,
} from './types';
import type { AwarenessState } from './awareness';
import { getColdZoneAt } from './awareness';
import {
  checkCollision,
  worldToGrid,
  gridToWorld,
  euclideanDistance,
  clampToMapBounds,
  getTileAt,
} from './collision';
import type { SimulatedNPC } from './usePatrolSimulation';
import { AlertState } from './alertSystem';
import type { CombatRenderState } from './combat';
import { CombatActionType, getActionRangeTiles, getCoverValueAtPosition } from './combat';
import type {
  ConsequenceHighlight,
  DormantThread,
  FactionPressure,
  FactionPressureZone,
} from './consequences';
import { FactionPressureOverlay } from './FactionPressureOverlay';
import { useAudio } from './useAudio';
import { useTutorial } from './useTutorial';

// ============================================================================
// Types
// ============================================================================

interface LocalMapCanvasProps {
  map: LocalMapTemplate;
  npcStates?: Map<string, SimulatedNPC>;
  initialPosition?: Point;
  initialFacing?: 'north' | 'south' | 'east' | 'west';
  onExitApproach?: (exit: MapExit) => void;
  onObjectInteract?: (object: MapObject) => void;
  onPositionChange?: (position: Point, gridPos: GridPosition) => void;
  onIdleChange?: (idleSeconds: number) => void;
  awarenessState?: Map<string, AwarenessState>;
  ambientShift?: number;
  factionPressures?: FactionPressure[];
  pressureZones?: FactionPressureZone[];
  dormantThreads?: DormantThread[];
  highlights?: ConsequenceHighlight[];
  paused?: boolean;
  dimmed?: boolean;
  onCanvasClick?: (position: Point, gridPos: GridPosition) => void;
  playerPositionOverride?: Point;
  playerFacingOverride?: 'north' | 'south' | 'east' | 'west';
  combatOverlay?: CombatRenderState | null;
}

interface InteractionPrompt {
  target: MapObject | MapExit;
  type: 'object' | 'exit';
  action: string;
  distance: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number; // 0-1
  size: number;
  color: string;
}

// ============================================================================
// Rendering Helpers
// ============================================================================

function drawTile(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
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
    // Gradient not supported on OffscreenCanvas in some envs, fallback to solid
    ctx.fillStyle = 'rgba(63, 185, 80, 0.1)';
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
  facing: 'north' | 'south' | 'east' | 'west',
  isMoving: boolean
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

function drawDetectionCone(
  ctx: CanvasRenderingContext2D,
  pos: Point,
  facing: 'north' | 'south' | 'east' | 'west',
  alertState: AlertState
) {
  const angles = {
    north: -Math.PI / 2,
    south: Math.PI / 2,
    east: 0,
    west: Math.PI,
  };
  const baseAngle = angles[facing];
  const length = 120;
  const spread = Math.PI / 3;

  ctx.save();
  ctx.translate(pos.x, pos.y);
  
  // Draw cone
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.arc(0, 0, length, baseAngle - spread/2, baseAngle + spread/2);
  ctx.lineTo(0, 0);
  
  let color = '255, 255, 255';
  if (alertState === AlertState.INVESTIGATING) color = '255, 200, 0';
  if (alertState === AlertState.COMBAT) color = '255, 0, 0';
  
  ctx.fillStyle = `rgba(${color}, 0.05)`;
  ctx.fill();
  
  ctx.restore();
}

function drawObject(
  ctx: CanvasRenderingContext2D,
  obj: MapObject,
  isNearby: boolean,
  isSelected: boolean,
  positionOverride?: Point,
  facingOverride?: 'north' | 'south' | 'east' | 'west',
  alertState?: AlertState,
  alertLevel?: number,
  time: number = 0
) {
  const pos = positionOverride || gridToWorld(obj.position.col, obj.position.row);
  const radius = 10;
  
  // Determine color based on type
  let color = ENTITY_COLORS.prop;
  if (obj.type === 'npc') {
    const npcData = obj.data as { disposition?: string } | undefined;
    const disposition = npcData?.disposition || 'neutral';
    const baseColor =
      ENTITY_COLORS.npc[disposition as keyof typeof ENTITY_COLORS.npc] || ENTITY_COLORS.npc.neutral;
    const intensity = getDispositionIntensity(disposition);
    color = applyColorIntensity(baseColor, intensity);
  } else if (obj.type === 'item') {
    color = ENTITY_COLORS.item;
  }

  // Draw detection cone if NPC
  if (obj.type === 'npc' && facingOverride && alertState) {
    drawDetectionCone(ctx, pos, facingOverride, alertState);
  }
  
  // Nearby highlight
  if (isNearby) {
    // Pulse effect
    const pulse = Math.sin(time / 200) * 0.1 + 0.15;
    
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, INTERACTION_RANGE, 0, Math.PI * 2);
    ctx.fillStyle = colorWithAlpha(color, pulse);
    ctx.fill();
    
    // Interaction ring (subtle expanding)
    const ringSize = (time % 1000) / 1000 * (INTERACTION_RANGE - radius) + radius;
    const ringAlpha = 1 - (time % 1000) / 1000;
    
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, ringSize, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(255, 255, 255, ${ringAlpha * 0.2})`;
    ctx.stroke();
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
  // Fade in effect could be added here if we tracked spawn time
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  
  // NPC facing indicator
  if (obj.type === 'npc') {
    const facing = facingOverride || (obj.data as { facing?: string })?.facing;
    
    if (facing) {
      const angles = {
        north: -Math.PI / 2,
        south: Math.PI / 2,
        east: 0,
        west: Math.PI,
      };
      const angle = angles[facing as keyof typeof angles] || 0;
      
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

  // Alert State Indicator
  if (alertState && alertState !== AlertState.PATROLLING) {
    ctx.fillStyle = alertState === AlertState.COMBAT ? '#f85149' : '#d29922';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    const floatY = Math.sin(time / 150) * 3;
    ctx.fillText('!', pos.x, pos.y - 15 + floatY);
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
  isNearby: boolean,
  time: number
) {
  const pos = gridToWorld(exit.position.col, exit.position.row);
  const color = exit.locked ? ENTITY_COLORS.exit.locked : ENTITY_COLORS.exit.open;
  
  // Exit glow when nearby
  if (isNearby && !exit.locked) {
    // Breathing glow
    const breath = Math.sin(time / 500) * 0.1 + 0.3;
    
    const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, TILE_SIZE);
    gradient.addColorStop(0, `rgba(63, 185, 80, ${breath})`);
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

function drawDormantThreadMarker(
  ctx: CanvasRenderingContext2D,
  thread: DormantThread,
  timeMs: number
) {
  const pos = gridToWorld(thread.spatial.position.col, thread.spatial.position.row);
  const pulse = 0.6 + 0.4 * Math.sin(timeMs / 700);
  const color =
    thread.severity === 'major'
      ? '248, 81, 73'
      : thread.severity === 'minor'
      ? '139, 148, 158'
      : '210, 153, 34';

  const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, 12);
  gradient.addColorStop(0, `rgba(${color}, ${0.25 * pulse})`);
  gradient.addColorStop(1, 'transparent');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, 12, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = `rgba(${color}, ${0.5 * pulse})`;
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, 2, 0, Math.PI * 2);
  ctx.fill();
}

function drawHighlight(
  ctx: CanvasRenderingContext2D,
  highlight: ConsequenceHighlight,
  timeMs: number
) {
  const pos = gridToWorld(highlight.position.col, highlight.position.row);
  const pulse = 0.7 + 0.3 * Math.sin(timeMs / 350);
  const color = highlight.color || '88, 166, 255';

  ctx.strokeStyle = `rgba(${color}, ${0.6 * pulse})`;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, 18 + 4 * pulse, 0, Math.PI * 2);
  ctx.stroke();
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

function drawTutorialHint(
  ctx: CanvasRenderingContext2D,
  hint: string,
  playerPos: Point
) {
  ctx.font = '12px "JetBrains Mono", monospace';
  const textWidth = ctx.measureText(hint).width;
  const padding = 8;
  const boxWidth = textWidth + padding * 2;
  const boxHeight = 26;
  
  const boxX = playerPos.x - boxWidth / 2;
  const boxY = playerPos.y - 50;
  
  // Background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
  ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
  
  // Border (Gold for tutorial)
  ctx.strokeStyle = '#d29922';
  ctx.lineWidth = 1;
  ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);
  
  // Text
  ctx.fillStyle = '#d29922';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(hint, boxX + boxWidth / 2, boxY + boxHeight / 2);
  
  // Arrow
  ctx.beginPath();
  ctx.moveTo(playerPos.x, boxY + boxHeight);
  ctx.lineTo(playerPos.x - 5, boxY + boxHeight + 5);
  ctx.lineTo(playerPos.x + 5, boxY + boxHeight + 5);
  ctx.fill();
}

function drawCoverHighlights(
  ctx: CanvasRenderingContext2D,
  map: LocalMapTemplate
) {
  for (let row = 0; row < map.height; row++) {
    for (let col = 0; col < map.width; col++) {
      const tile = map.tiles[row][col];
      const coverValue = TILE_PROPERTIES[tile].coverValue;
      if (coverValue <= 0) continue;

      const x = col * TILE_SIZE;
      const y = row * TILE_SIZE;
      ctx.fillStyle = coverValue >= 2
        ? 'rgba(88, 166, 255, 0.18)'
        : 'rgba(86, 212, 221, 0.12)';
      ctx.fillRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);
    }
  }
}

function drawMovementRange(
  ctx: CanvasRenderingContext2D,
  position: Point,
  range: number,
  color: string
) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.arc(position.x, position.y, range, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function drawTargetLine(
  ctx: CanvasRenderingContext2D,
  from: Point,
  to: Point,
  color: string
) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 6]);
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();
  ctx.restore();
}

function drawIntentArrow(
  ctx: CanvasRenderingContext2D,
  from: Point,
  to: Point,
  color: string
) {
  const angle = Math.atan2(to.y - from.y, to.x - from.x);
  const arrowLength = 10;

  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(to.x, to.y);
  ctx.lineTo(
    to.x - arrowLength * Math.cos(angle - Math.PI / 6),
    to.y - arrowLength * Math.sin(angle - Math.PI / 6)
  );
  ctx.lineTo(
    to.x - arrowLength * Math.cos(angle + Math.PI / 6),
    to.y - arrowLength * Math.sin(angle + Math.PI / 6)
  );
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawTargetRing(
  ctx: CanvasRenderingContext2D,
  position: Point,
  coverValue: number,
  inRange: boolean
) {
  const baseColor = coverValue >= 2
    ? 'rgba(248, 81, 73, 0.7)'
    : coverValue === 1
    ? 'rgba(210, 153, 34, 0.7)'
    : 'rgba(86, 212, 221, 0.7)';

  ctx.save();
  ctx.strokeStyle = inRange ? baseColor : 'rgba(110, 118, 129, 0.5)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(position.x, position.y, 16, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function isTargetingAction(action: CombatActionType | null | undefined): boolean {
  return (
    action === CombatActionType.FIRE ||
    action === CombatActionType.STRIKE ||
    action === CombatActionType.SUPPRESS
  );
}

function adjustBrightness(hex: string, factor: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  
  const nr = clampColor(Math.round(r * factor));
  const ng = clampColor(Math.round(g * factor));
  const nb = clampColor(Math.round(b * factor));
  
  return `rgb(${nr}, ${ng}, ${nb})`;
}

function applyColorIntensity(hex: string, intensity: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);

  const nr = clampColor(Math.round(r * intensity));
  const ng = clampColor(Math.round(g * intensity));
  const nb = clampColor(Math.round(b * intensity));

  return `rgb(${nr}, ${ng}, ${nb})`;
}

function colorWithAlpha(color: string, alpha: number): string {
  if (color.startsWith('#')) {
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  const rgbMatch = color.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/i);
  if (rgbMatch) {
    return `rgba(${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]}, ${alpha})`;
  }

  return color;
}

function getDispositionIntensity(disposition: string): number {
  switch (disposition) {
    case 'hostile':
      return 1.15;
    case 'wary':
      return 1.05;
    case 'warm':
      return 0.92;
    case 'loyal':
      return 0.9;
    default:
      return 1.0;
  }
}

function clampColor(value: number): number {
  return Math.max(0, Math.min(255, value));
}

// ============================================================================
// Component
// ============================================================================

export function LocalMapCanvas({
  map,
  npcStates,
  initialPosition,
  initialFacing = 'south',
  onExitApproach,
  onObjectInteract,
  onPositionChange,
  onIdleChange,
  awarenessState,
  ambientShift = 0,
  factionPressures = [],
  pressureZones = [],
  dormantThreads = [],
  highlights = [],
  paused = false,
  dimmed = false,
  onCanvasClick,
  playerPositionOverride,
  playerFacingOverride,
  combatOverlay,
}: LocalMapCanvasProps) {
  const baseCanvasRef = useRef<HTMLCanvasElement>(null);
  const entityCanvasRef = useRef<HTMLCanvasElement>(null);
  const combatCanvasRef = useRef<HTMLCanvasElement>(null);
  const keysPressed = useRef<Set<string>>(new Set());
  
  // Hooks
  const audio = useAudio();
  const tutorial = useTutorial();
  
  // Initialization
  const defaultSpawn = map.spawnPoints.find(sp => sp.isDefault) || map.spawnPoints[0];
  const startPos = initialPosition || (defaultSpawn 
    ? gridToWorld(defaultSpawn.position.col, defaultSpawn.position.row)
    : { x: map.width * TILE_SIZE / 2, y: map.height * TILE_SIZE / 2 });
  
  const [playerPos, setPlayerPos] = useState<Point>(startPos);
  const playerPosRef = useRef<Point>(startPos);
  const lastMoveAtRef = useRef<number>(performance.now());
  const lastIdleReportRef = useRef<number>(0);
  const [playerFacing, setPlayerFacing] = useState<'north' | 'south' | 'east' | 'west'>(
    initialFacing || (defaultSpawn?.facing as typeof initialFacing) || 'south'
  );
  
  const [nearbyObjects, setNearbyObjects] = useState<MapObject[]>([]);
  const [nearbyExits, setNearbyExits] = useState<MapExit[]>([]);
  const [activePrompt, setActivePrompt] = useState<InteractionPrompt | null>(null);
  
  // Particles
  const particlesRef = useRef<Particle[]>([]);
  const footstepDistRef = useRef<number>(0);
  
  // Offscreen canvas for map cache
  const mapCacheRef = useRef<OffscreenCanvas | HTMLCanvasElement | null>(null);
  const mapCacheCtxRef = useRef<OffscreenCanvasRenderingContext2D | CanvasRenderingContext2D | null>(null);
  const prevMapRef = useRef<string>('');
  const prevAmbientRef = useRef<number>(-1);
  
  const canvasWidth = map.width * TILE_SIZE;
  const canvasHeight = map.height * TILE_SIZE;

  const handleCanvasClick = useCallback((event: MouseEvent<HTMLCanvasElement>) => {
    if (!onCanvasClick) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const scaleX = canvasWidth / rect.width;
    const scaleY = canvasHeight / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    onCanvasClick({ x, y }, worldToGrid(x, y));
  }, [onCanvasClick, canvasWidth, canvasHeight]);

  // Update atmosphere audio
  useEffect(() => {
    audio.setAtmosphere(map.atmosphere);
  }, [map.atmosphere]);

  // Sync ref
  useEffect(() => {
    playerPosRef.current = playerPos;
    lastMoveAtRef.current = performance.now();
  }, [playerPos]);

  useEffect(() => {
    if (!playerPositionOverride) return;
    const next = playerPositionOverride;
    const current = playerPosRef.current;
    if (current.x === next.x && current.y === next.y) return;
    playerPosRef.current = next;
    setPlayerPos(next);
  }, [playerPositionOverride?.x, playerPositionOverride?.y]);

  useEffect(() => {
    if (!playerFacingOverride) return;
    setPlayerFacing(playerFacingOverride);
  }, [playerFacingOverride]);
  
  // Proximity Logic
  useEffect(() => {
    const coldZone = getColdZoneAt(map, playerPos);
    const suppressPrompts = !!coldZone?.suppressPrompts;

    if (suppressPrompts) {
      setNearbyObjects([]);
      setNearbyExits([]);
      setActivePrompt(null);
      return;
    }

    const nearby: MapObject[] = [];
    let closestDist = INTERACTION_RANGE;
    let closestPrompt: InteractionPrompt | null = null;

    // Check objects
    for (const obj of map.objects) {
      if (!isObjectInteractable(obj)) continue;

      let objPos: Point;
      if (obj.type === 'npc' && npcStates?.has(obj.id)) {
        objPos = npcStates.get(obj.id)!.position;
      } else {
        objPos = gridToWorld(obj.position.col, obj.position.row);
      }
      
      const dist = euclideanDistance(playerPos, objPos);
      if (dist < INTERACTION_RANGE) {
        nearby.push(obj);
        
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
    }
    setNearbyObjects(nearby);
    
    // Check exits
    const nearExits: MapExit[] = [];
    for (const exit of map.exits) {
      const exitPos = gridToWorld(exit.position.col, exit.position.row);
      const dist = euclideanDistance(playerPos, exitPos);
      if (dist < INTERACTION_RANGE) {
        nearExits.push(exit);
        if (!exit.locked) {
          onExitApproach?.(exit);
        }
        
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
    }
    setNearbyExits(nearExits);
    setActivePrompt(closestPrompt);

    // Tutorial Triggers
    if (closestPrompt && closestPrompt.distance < 40) {
      tutorial.onApproach(closestPrompt.distance);
    }

  }, [playerPos, map, onExitApproach, npcStates]);
  
  // Notify position changes
  useEffect(() => {
    const gridPos = worldToGrid(playerPos.x, playerPos.y);
    onPositionChange?.(playerPos, gridPos);
  }, [playerPos, onPositionChange]);
  
  // Game Loop
  useEffect(() => {
    if (paused) return;
    
    let animationId: number;
    
    function update() {
      const now = performance.now();
      const keys = keysPressed.current;
      let vx = 0;
      let vy = 0;
      let newFacing: typeof playerFacing | null = null;
      let isMoving = false;
      
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

      const currentPos = playerPosRef.current;
      let nextPos = currentPos;

      if (vx !== 0 || vy !== 0) {
        isMoving = true;
        tutorial.onMove();
        
        const targetPos = { x: currentPos.x + vx, y: currentPos.y + vy };
        const clamped = clampToMapBounds(map, targetPos, PLAYER_RADIUS);
        const collision = checkCollision(map, currentPos, clamped, PLAYER_RADIUS);
        nextPos = collision.newPosition;
        
        // Footsteps & Dust
        const dist = Math.sqrt(vx*vx + vy*vy);
        footstepDistRef.current += dist;
        
        if (footstepDistRef.current > 24) {
          footstepDistRef.current = 0;
          
          // Determine floor type
          const gridPos = worldToGrid(nextPos.x, nextPos.y);
          const tile = getTileAt(map, gridPos.col, gridPos.row);
          let floorType: any = 'default';
          if (tile === TileType.WATER) floorType = 'water';
          if (tile === TileType.DEBRIS) floorType = 'debris';
          // Metal check? Maybe by map ID or region
          if (map.id.includes('lab') || map.id.includes('bunker')) floorType = 'metal';
          
          audio.playFootstep(floorType);
          
          // Spawn dust
          for (let i = 0; i < 2; i++) {
            particlesRef.current.push({
              x: nextPos.x + (Math.random() - 0.5) * 10,
              y: nextPos.y + 10 + (Math.random() - 0.5) * 4,
              vx: (Math.random() - 0.5) * 0.5,
              vy: (Math.random() * -0.5),
              life: 1.0,
              size: Math.random() * 2 + 1,
              color: 'rgba(150, 150, 150, 0.4)',
            });
          }
        }
      }

      // Update particles
      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        const p = particlesRef.current[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.05;
        if (p.life <= 0) {
          particlesRef.current.splice(i, 1);
        }
      }

      if (nextPos.x !== currentPos.x || nextPos.y !== currentPos.y) {
        playerPosRef.current = nextPos;
        setPlayerPos(nextPos);
        lastMoveAtRef.current = now;
      }

      const idleSeconds = (now - lastMoveAtRef.current) / 1000;
      if (Math.abs(idleSeconds - lastIdleReportRef.current) >= 0.25) {
        lastIdleReportRef.current = idleSeconds;
        onIdleChange?.(idleSeconds);
      }
      
      animationId = requestAnimationFrame(update);
    }
    
    animationId = requestAnimationFrame(update);
    return () => cancelAnimationFrame(animationId);
  }, [map, paused, onIdleChange]);
  
  // Keyboard handlers
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const key = e.key.toLowerCase();
      keysPressed.current.add(key);
      
      // Interaction
      if (key === 'e' && !paused) {
        if (activePrompt) {
          tutorial.onInteract();
          audio.playInteraction('select');
          if (activePrompt.type === 'object') {
            onObjectInteract?.(activePrompt.target as MapObject);
          } else if (activePrompt.type === 'exit') {
            const exit = activePrompt.target as MapExit;
            if (!exit.locked) {
              onExitApproach?.(exit);
            } else {
              audio.playInteraction('cancel');
            }
          }
        } else {
          audio.playInteraction('cancel');
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
  
  // Cache map tiles
  useEffect(() => {
    const baseAmbient = dimmed ? map.ambientLight * 0.5 : map.ambientLight;
    const ambientLight = Math.max(0.05, Math.min(1, baseAmbient + ambientShift));
    
    // Only rebuild cache if map or lighting changed significantly
    if (mapCacheRef.current && 
        prevMapRef.current === map.id && 
        Math.abs(prevAmbientRef.current - ambientLight) < 0.05) {
      return;
    }
    
    if (!mapCacheRef.current || 
        mapCacheRef.current.width !== canvasWidth || 
        mapCacheRef.current.height !== canvasHeight) {
          
      if (typeof OffscreenCanvas !== 'undefined') {
        mapCacheRef.current = new OffscreenCanvas(canvasWidth, canvasHeight);
      } else {
        mapCacheRef.current = document.createElement('canvas');
        mapCacheRef.current.width = canvasWidth;
        mapCacheRef.current.height = canvasHeight;
      }
      mapCacheCtxRef.current = mapCacheRef.current.getContext('2d') as any;
    }

    const ctx = mapCacheCtxRef.current;
    if (!ctx) return;

    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // Draw tiles to cache
    for (let row = 0; row < map.height; row++) {
      for (let col = 0; col < map.width; col++) {
        drawTile(ctx, col, row, map.tiles[row][col], ambientLight);
      }
    }
    
    prevMapRef.current = map.id;
    prevAmbientRef.current = ambientLight;

    const baseCanvas = baseCanvasRef.current;
    if (baseCanvas) {
      const baseCtx = baseCanvas.getContext('2d');
      if (baseCtx) {
        baseCtx.clearRect(0, 0, canvasWidth, canvasHeight);
        if (mapCacheRef.current) {
          baseCtx.drawImage(mapCacheRef.current, 0, 0);
        }
      }
    }
  }, [map, canvasWidth, canvasHeight, ambientShift, dimmed]);

  // Render Frame
  useEffect(() => {
    const canvas = entityCanvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    const now = performance.now();

    // Draw dormant thread markers
    for (const thread of dormantThreads) {
      if (thread.spatial.mapId !== map.id) continue;
      drawDormantThreadMarker(ctx, thread, now);
    }

    // Draw exits (dynamic parts)
    for (const exit of map.exits) {
      const isNearby = nearbyExits.includes(exit);
      drawExit(ctx, exit, isNearby, now);
    }
    
    // Draw particles (behind objects)
    for (const p of particlesRef.current) {
      ctx.globalAlpha = p.life;
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x, p.y, p.size, p.size);
    }
    ctx.globalAlpha = 1.0;
    
    // Draw objects
    // Sort by Y for depth
    const sortedObjects = [...map.objects].sort((a, b) => {
      const ay = a.position.row * TILE_SIZE;
      const by = b.position.row * TILE_SIZE;
      return ay - by;
    });

    for (const obj of sortedObjects) {
      const isNearby = nearbyObjects.includes(obj);
      const isSelected = activePrompt?.type === 'object' && 
        (activePrompt.target as MapObject).id === obj.id;
        
      let posOverride: Point | undefined;
      let facingOverride: 'north' | 'south' | 'east' | 'west' | undefined;
      let alertState: AlertState | undefined;
      let alertLevel: number | undefined;

      if (obj.type === 'npc' && npcStates?.has(obj.id)) {
        const sim = npcStates.get(obj.id)!;
        const awareness = awarenessState?.get(obj.id);
        const offset = awareness?.positionOffset;
        posOverride = offset
          ? { x: sim.position.x + offset.x, y: sim.position.y + offset.y }
          : sim.position;
        facingOverride = awareness?.facingOverride || sim.facing;
        alertState = sim.alertState;
        alertLevel = sim.alertLevel;
      } else if (obj.type === 'npc') {
        const awareness = awarenessState?.get(obj.id);
        const offset = awareness?.positionOffset;
        const basePos = gridToWorld(obj.position.col, obj.position.row);
        posOverride = offset
          ? { x: basePos.x + offset.x, y: basePos.y + offset.y }
          : undefined;
        facingOverride = awareness?.facingOverride;
      }

      drawObject(
        ctx, 
        obj, 
        isNearby, 
        isSelected, 
        posOverride, 
        facingOverride, 
        alertState, 
        alertLevel,
        now
      );
    }
    
    // Draw player
    drawPlayer(ctx, playerPos, playerFacing, false);

    // Draw highlights
    const activeHighlights = highlights.filter(highlight => {
      if (highlight.mapId !== map.id) return false;
      if (!highlight.durationMs) return true;
      return now - highlight.createdAt <= highlight.durationMs;
    });

    for (const highlight of activeHighlights) {
      drawHighlight(ctx, highlight, now);
    }
    
    // Draw tutorial hint
    const hint = tutorial.getHint(
      nearbyObjects.length > 0 ? 'interaction' :
      nearbyExits.length > 0 ? 'interaction' :
      'movement'
    );
    
    if (hint && !activePrompt && !dimmed) {
       drawTutorialHint(ctx, hint, playerPos);
    }

    // Draw interaction prompt
    if (activePrompt) {
      drawInteractionPrompt(ctx, activePrompt, canvasWidth);
    }

    // Draw map info overlay
    drawMapInfo(ctx, map.name, map.atmosphere, canvasWidth);
    
  }, [
    map,
    playerPos,
    playerFacing,
    nearbyObjects,
    nearbyExits,
    activePrompt,
    canvasWidth,
    canvasHeight,
    npcStates,
    awarenessState,
    ambientShift,
    dimmed,
    dormantThreads,
    highlights,
    tutorial // Re-render when tutorial state changes
  ]);

  useEffect(() => {
    const canvas = combatCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    if (!combatOverlay?.active) return;

    const combatantById = new Map(combatOverlay.combatants.map(combatant => [combatant.id, combatant]));
    const player = combatantById.get(combatOverlay.playerId);

    drawCoverHighlights(ctx, map);

    const activeId = combatOverlay.activeCombatantId || combatOverlay.playerId;
    const activeCombatant = combatantById.get(activeId);
    if (activeCombatant) {
      const color = activeCombatant.isPlayer ? 'rgba(86, 212, 221, 0.7)' : 'rgba(248, 81, 73, 0.7)';
      drawMovementRange(ctx, activeCombatant.position, combatOverlay.movementRange, color);
    }

    if (player && isTargetingAction(combatOverlay.selectedAction)) {
      const rangeTiles = getActionRangeTiles(combatOverlay.selectedAction || CombatActionType.FIRE);

      combatOverlay.combatants
        .filter(combatant => !combatant.isPlayer && combatant.status === 'active')
        .forEach(combatant => {
          const distance = euclideanDistance(player.position, combatant.position) / TILE_SIZE;
          const coverValue = getCoverValueAtPosition(map, combatant.position);
          drawTargetRing(ctx, combatant.position, coverValue, distance <= rangeTiles);
        });

      if (combatOverlay.selectedTargetId) {
        const target = combatantById.get(combatOverlay.selectedTargetId);
        if (target) {
          drawTargetLine(ctx, player.position, target.position, 'rgba(88, 166, 255, 0.8)');
        }
      }
    }

    combatOverlay.intents.forEach(intent => {
      const npc = combatantById.get(intent.npcId);
      if (!npc) return;
      let targetPos = intent.targetPosition;
      if (!targetPos && intent.targetId) {
        targetPos = combatantById.get(intent.targetId)?.position;
      }
      if (!targetPos && player) {
        targetPos = player.position;
      }
      if (!targetPos) return;
      const intentColor = intent.action === CombatActionType.FLEE
        ? 'rgba(110, 118, 129, 0.6)'
        : intent.action === CombatActionType.MOVE
        ? 'rgba(86, 212, 221, 0.6)'
        : 'rgba(248, 81, 73, 0.6)';
      drawIntentArrow(ctx, npc.position, targetPos, intentColor);
    });
  }, [combatOverlay, map, canvasWidth, canvasHeight]);
  
  return (
    <div
      className="localmap-canvas-stack"
      style={{ width: canvasWidth, height: canvasHeight }}
    >
      <canvas
        ref={baseCanvasRef}
        width={canvasWidth}
        height={canvasHeight}
        className="localmap-layer localmap-layer-base"
      />
      <FactionPressureOverlay
        map={map}
        pressures={factionPressures}
        zones={pressureZones}
        tileSize={map.tileSize || TILE_SIZE}
        active={!paused}
      />
      <canvas
        ref={entityCanvasRef}
        width={canvasWidth}
        height={canvasHeight}
        className="localmap-layer localmap-layer-entities"
        onClick={handleCanvasClick}
        tabIndex={0}
      />
      <canvas
        ref={combatCanvasRef}
        width={canvasWidth}
        height={canvasHeight}
        className="localmap-layer localmap-layer-combat"
      />
      {dimmed && <div className="localmap-dim-overlay" />}
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function isObjectInteractable(obj: MapObject): boolean {
  if (obj.interactionDisabled) return false;

  if (obj.type === 'npc') {
    const npcData = obj.data as NPCObjectData | undefined;
    const behavior = npcData?.behaviorState;
    if (behavior === NPCBehaviorState.BUSY || behavior === NPCBehaviorState.UNAVAILABLE) {
      return false;
    }
    if (npcData?.fleeOnApproach) return false;
  }

  if (obj.type === 'prop') {
    const propData = obj.data as { interactable?: boolean } | undefined;
    if (propData?.interactable === false) return false;
  }

  if (obj.type === 'item') {
    const itemData = obj.data as { hidden?: boolean } | undefined;
    if (itemData?.hidden) return false;
  }

  return true;
}

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
