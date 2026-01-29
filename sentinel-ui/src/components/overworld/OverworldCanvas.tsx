/**
 * OverworldCanvas — Canvas-based overworld renderer
 * 
 * Renders the current region with player, NPCs, hazards, and exits.
 * Movement is free but non-authoritative — proximity alone never commits.
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import type {
  OverworldState,
  Entity,
  Point,
  ProximityPrompt,
  MovementState,
  TerrainType,
} from './types';
import {
  COLORS,
  MOVEMENT_SPEED,
  PLAYER_RADIUS,
  INTERACTION_RADIUS,
} from './types';

interface OverworldCanvasProps {
  state: OverworldState;
  width: number;
  height: number;
  onEntityInteract?: (entity: Entity) => void;
  onExitApproach?: (entity: Entity) => void;
}

// ============================================================================
// Rendering Helpers
// ============================================================================

function drawTerrain(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  terrain: TerrainType[]
) {
  // Base terrain color
  const primaryTerrain = terrain[0] || 'urban';
  ctx.fillStyle = COLORS.terrain[primaryTerrain] || COLORS.bg.primary;
  ctx.fillRect(0, 0, width, height);

  // Grid overlay
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
  ctx.lineWidth = 1;
  const gridSize = 32;
  
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Terrain texture (noise-like pattern)
  ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
  for (let i = 0; i < 100; i++) {
    const x = Math.random() * width;
    const y = Math.random() * height;
    const size = Math.random() * 3 + 1;
    ctx.fillRect(x, y, size, size);
  }
}

function drawEntity(
  ctx: CanvasRenderingContext2D,
  entity: Entity,
  isNearby: boolean,
  isSelected: boolean
) {
  const { position, radius, type, label, data } = entity;

  // Entity color based on type
  let color = COLORS.entity.player;
  switch (type) {
    case 'player':
      color = COLORS.entity.player;
      break;
    case 'npc':
      const npcData = data as { disposition?: string } | undefined;
      const disposition = npcData?.disposition || 'neutral';
      color = COLORS.entity.npc[disposition as keyof typeof COLORS.entity.npc] || COLORS.entity.npc.neutral;
      break;
    case 'hazard':
      color = COLORS.entity.hazard;
      break;
    case 'poi':
      color = COLORS.entity.poi;
      break;
    case 'exit':
      const exitData = data as { traversable?: boolean } | undefined;
      color = exitData?.traversable ? COLORS.entity.exit.open : COLORS.entity.exit.blocked;
      break;
  }

  // Interaction radius (when nearby)
  if (isNearby && type !== 'player') {
    ctx.beginPath();
    ctx.arc(position.x, position.y, INTERACTION_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = `${color}15`;
    ctx.fill();
    ctx.strokeStyle = `${color}40`;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Selection highlight
  if (isSelected) {
    ctx.beginPath();
    ctx.arc(position.x, position.y, radius + 8, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Entity body
  ctx.beginPath();
  ctx.arc(position.x, position.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();

  // Entity icon/indicator
  ctx.fillStyle = COLORS.bg.primary;
  ctx.font = `${radius}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  
  const icon = getEntityIcon(type);
  ctx.fillText(icon, position.x, position.y);

  // Label (when nearby or selected)
  if (isNearby || isSelected) {
    ctx.fillStyle = color;
    ctx.font = '11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(label, position.x, position.y - radius - 8);
  }
}

function getEntityIcon(type: Entity['type']): string {
  switch (type) {
    case 'player': return '▲';
    case 'npc': return '●';
    case 'hazard': return '⚠';
    case 'poi': return '◆';
    case 'exit': return '→';
    default: return '?';
  }
}

function drawPlayer(
  ctx: CanvasRenderingContext2D,
  position: Point,
  direction: MovementState['direction']
) {
  // Player glow
  const gradient = ctx.createRadialGradient(
    position.x, position.y, 0,
    position.x, position.y, PLAYER_RADIUS * 2
  );
  gradient.addColorStop(0, `${COLORS.entity.player}40`);
  gradient.addColorStop(1, 'transparent');
  ctx.fillStyle = gradient;
  ctx.fillRect(
    position.x - PLAYER_RADIUS * 2,
    position.y - PLAYER_RADIUS * 2,
    PLAYER_RADIUS * 4,
    PLAYER_RADIUS * 4
  );

  // Player body
  ctx.beginPath();
  ctx.arc(position.x, position.y, PLAYER_RADIUS, 0, Math.PI * 2);
  ctx.fillStyle = COLORS.entity.player;
  ctx.fill();

  // Direction indicator
  if (direction) {
    const angle = {
      up: -Math.PI / 2,
      down: Math.PI / 2,
      left: Math.PI,
      right: 0,
    }[direction];

    ctx.save();
    ctx.translate(position.x, position.y);
    ctx.rotate(angle);
    ctx.beginPath();
    ctx.moveTo(PLAYER_RADIUS + 4, 0);
    ctx.lineTo(PLAYER_RADIUS - 2, -4);
    ctx.lineTo(PLAYER_RADIUS - 2, 4);
    ctx.closePath();
    ctx.fillStyle = COLORS.entity.player;
    ctx.fill();
    ctx.restore();
  }

  // Player icon
  ctx.fillStyle = COLORS.bg.primary;
  ctx.font = `${PLAYER_RADIUS}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('▲', position.x, position.y);
}

function drawProximityPrompt(
  ctx: CanvasRenderingContext2D,
  prompt: ProximityPrompt,
  canvasWidth: number
) {
  const { entity, action, cost } = prompt;
  
  // Prompt box
  const text = cost ? `[E] ${action} (${cost})` : `[E] ${action}`;
  ctx.font = '12px "JetBrains Mono", monospace';
  const textWidth = ctx.measureText(text).width;
  const padding = 8;
  const boxWidth = textWidth + padding * 2;
  const boxHeight = 24;
  
  let boxX = entity.position.x - boxWidth / 2;
  const boxY = entity.position.y + entity.radius + 16;
  
  // Keep prompt on screen
  if (boxX < 10) boxX = 10;
  if (boxX + boxWidth > canvasWidth - 10) boxX = canvasWidth - boxWidth - 10;

  // Background
  ctx.fillStyle = COLORS.ui.promptBg;
  ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
  
  // Border
  ctx.strokeStyle = COLORS.ui.prompt;
  ctx.lineWidth = 1;
  ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

  // Text
  ctx.fillStyle = COLORS.ui.prompt;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, boxX + boxWidth / 2, boxY + boxHeight / 2);
}

function drawRegionInfo(
  ctx: CanvasRenderingContext2D,
  regionName: string,
  width: number
) {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.fillRect(0, 0, width, 32);
  
  ctx.fillStyle = COLORS.entity.player;
  ctx.font = '12px "JetBrains Mono", monospace';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(regionName.toUpperCase(), 12, 16);
}

// ============================================================================
// Component
// ============================================================================

export function OverworldCanvas({
  state,
  width,
  height,
  onEntityInteract,
  onExitApproach,
}: OverworldCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [playerPos, setPlayerPos] = useState<Point>(state.player.position);
  const [movement, setMovement] = useState<MovementState>({
    velocity: { x: 0, y: 0 },
    isMoving: false,
    direction: null,
  });
  const [nearbyEntities, setNearbyEntities] = useState<Entity[]>([]);
  const [activePrompt, setActivePrompt] = useState<ProximityPrompt | null>(null);
  const keysPressed = useRef<Set<string>>(new Set());

  // Calculate nearby entities
  useEffect(() => {
    const nearby = state.entities.filter(entity => {
      const dx = entity.position.x - playerPos.x;
      const dy = entity.position.y - playerPos.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < INTERACTION_RADIUS + entity.radius;
    });
    setNearbyEntities(nearby);

    // Set active prompt for closest entity
    if (nearby.length > 0) {
      const closest = nearby.reduce((a, b) => {
        const distA = Math.sqrt(
          Math.pow(a.position.x - playerPos.x, 2) +
          Math.pow(a.position.y - playerPos.y, 2)
        );
        const distB = Math.sqrt(
          Math.pow(b.position.x - playerPos.x, 2) +
          Math.pow(b.position.y - playerPos.y, 2)
        );
        return distA < distB ? a : b;
      });

      const distance = Math.sqrt(
        Math.pow(closest.position.x - playerPos.x, 2) +
        Math.pow(closest.position.y - playerPos.y, 2)
      );

      setActivePrompt({
        entity: closest,
        distance,
        action: getInteractionAction(closest),
        cost: getInteractionCost(closest),
      });
    } else {
      setActivePrompt(null);
    }
  }, [playerPos, state.entities]);

  // Check for exit approach
  useEffect(() => {
    for (const exit of state.exits) {
      const dx = exit.position.x - playerPos.x;
      const dy = exit.position.y - playerPos.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance < INTERACTION_RADIUS) {
        onExitApproach?.(exit);
        break;
      }
    }
  }, [playerPos, state.exits, onExitApproach]);

  // Movement loop
  useEffect(() => {
    let animationId: number;

    function updateMovement() {
      const keys = keysPressed.current;
      let vx = 0;
      let vy = 0;
      let direction: MovementState['direction'] = null;

      if (keys.has('w') || keys.has('arrowup')) { vy = -MOVEMENT_SPEED; direction = 'up'; }
      if (keys.has('s') || keys.has('arrowdown')) { vy = MOVEMENT_SPEED; direction = 'down'; }
      if (keys.has('a') || keys.has('arrowleft')) { vx = -MOVEMENT_SPEED; direction = 'left'; }
      if (keys.has('d') || keys.has('arrowright')) { vx = MOVEMENT_SPEED; direction = 'right'; }

      // Diagonal movement
      if (vx !== 0 && vy !== 0) {
        const factor = 1 / Math.sqrt(2);
        vx *= factor;
        vy *= factor;
      }

      setMovement({
        velocity: { x: vx, y: vy },
        isMoving: vx !== 0 || vy !== 0,
        direction,
      });

      if (vx !== 0 || vy !== 0) {
        setPlayerPos(prev => {
          const newX = Math.max(PLAYER_RADIUS, Math.min(width - PLAYER_RADIUS, prev.x + vx));
          const newY = Math.max(PLAYER_RADIUS + 32, Math.min(height - PLAYER_RADIUS, prev.y + vy));
          return { x: newX, y: newY };
        });
      }

      animationId = requestAnimationFrame(updateMovement);
    }

    animationId = requestAnimationFrame(updateMovement);
    return () => cancelAnimationFrame(animationId);
  }, [width, height]);

  // Keyboard handlers
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const key = e.key.toLowerCase();
      keysPressed.current.add(key);

      // Interaction key
      if (key === 'e' && activePrompt) {
        onEntityInteract?.(activePrompt.entity);
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
  }, [activePrompt, onEntityInteract]);

  // Render
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Draw terrain
    drawTerrain(ctx, width, height, state.region.terrain);

    // Draw exits
    for (const exit of state.exits) {
      const isNearby = nearbyEntities.some(e => e.id === exit.id);
      drawEntity(ctx, exit, isNearby, false);
    }

    // Draw entities
    for (const entity of state.entities) {
      const isNearby = nearbyEntities.some(e => e.id === entity.id);
      const isSelected = activePrompt?.entity.id === entity.id;
      drawEntity(ctx, entity, isNearby, isSelected);
    }

    // Draw player
    drawPlayer(ctx, playerPos, movement.direction);

    // Draw proximity prompt
    if (activePrompt) {
      drawProximityPrompt(ctx, activePrompt, width);
    }

    // Draw region info
    drawRegionInfo(ctx, state.region.name, width);
  }, [state, playerPos, movement, nearbyEntities, activePrompt, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ display: 'block', background: COLORS.bg.primary }}
      tabIndex={0}
    />
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getInteractionAction(entity: Entity): string {
  switch (entity.type) {
    case 'npc': return `Talk to ${entity.label}`;
    case 'hazard': return 'Assess Risk';
    case 'poi': return `Investigate ${entity.label}`;
    case 'exit': return `Travel to ${entity.label}`;
    default: return 'Interact';
  }
}

function getInteractionCost(entity: Entity): string | undefined {
  switch (entity.type) {
    case 'npc': return undefined;
    case 'hazard': return undefined;
    case 'poi': return undefined;
    case 'exit': return '1 turn';
    default: return undefined;
  }
}
