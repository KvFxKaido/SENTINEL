/**
 * NPC Awareness System (Phase 2.5)
 *
 * Tracks proximity-based awareness, glance behavior, and subtle shifts
 * without triggering explicit UI feedback.
 */

import { useEffect, useRef, useState } from 'react';
import type { ColdZone, LocalMapTemplate, NPCObjectData, Point } from './types';
import { INTERACTION_RANGE, NPC_DETECTION_RANGE } from './types';
import { euclideanDistance, gridToWorld, hasLineOfSight, worldToGrid } from './collision';

// ============================================================================
// Types
// ============================================================================

export interface AwarenessState {
  npcId: string;
  aware: boolean;
  alert: boolean;
  proximitySeconds: number;
  lingerSeconds: number;
  glanceUntil: number;
  nextGlanceAt: number;
  glanceIntervalMs: number;
  facingOverride?: 'north' | 'south' | 'east' | 'west';
  shiftUntil: number;
  shiftOffset: Point;
  fleeUntil: number;
  fleeOffset: Point;
  lastShiftAt: number;
  lastFleeAt: number;
  positionOffset: Point;
}

export interface AwarenessSnapshot {
  states: Map<string, AwarenessState>;
  anyAware: boolean;
  ambientShift: number;
  idleSeconds: number;
}

export interface AwarenessOptions {
  map: LocalMapTemplate;
  playerPosition: Point;
  paused: boolean;
  idleSeconds: number;
  npcPositions?: Map<string, Point>;
}

// ============================================================================
// Constants
// ============================================================================

const AWARE_THRESHOLD_SECONDS = 3;
const LINGER_THRESHOLD_SECONDS = 10;
const IDLE_LINGER_GATE_SECONDS = 5;
const GLANCE_DURATION_MS = 650;
const UPDATE_INTERVAL_MS = 250;
const SHIFT_COOLDOWN_MS = 6000;
const SHIFT_DURATION_MS = 1400;
const FLEE_COOLDOWN_MS = 4500;
const FLEE_DURATION_MS = 1100;

// ============================================================================
// Hook
// ============================================================================

export function useNpcAwareness({
  map,
  playerPosition,
  paused,
  idleSeconds,
  npcPositions,
}: AwarenessOptions): AwarenessSnapshot {
  const [snapshot, setSnapshot] = useState<AwarenessSnapshot>(() => ({
    states: new Map(),
    anyAware: false,
    ambientShift: 0,
    idleSeconds,
  }));

  const statesRef = useRef<Map<string, AwarenessState>>(new Map());
  const lastUpdateRef = useRef<number>(performance.now());
  const playerRef = useRef<Point>(playerPosition);
  const idleRef = useRef<number>(idleSeconds);
  const npcPositionsRef = useRef<Map<string, Point> | undefined>(undefined);

  useEffect(() => {
    playerRef.current = playerPosition;
  }, [playerPosition]);

  useEffect(() => {
    idleRef.current = idleSeconds;
  }, [idleSeconds]);

  useEffect(() => {
    npcPositionsRef.current = npcPositions;
  }, [npcPositions]);

  // Reset awareness when map changes
  useEffect(() => {
    statesRef.current = new Map();
    lastUpdateRef.current = performance.now();
    setSnapshot({
      states: new Map(),
      anyAware: false,
      ambientShift: 0,
      idleSeconds: idleRef.current,
    });
  }, [map.id]);

  useEffect(() => {
    if (paused) return;

    const intervalId = window.setInterval(() => {
      const now = performance.now();
      const deltaSeconds = Math.min(0.5, (now - lastUpdateRef.current) / 1000);
      lastUpdateRef.current = now;

      updateNpcAwareness(
        map,
        playerRef.current,
        idleRef.current,
        now,
        deltaSeconds,
        statesRef.current,
        npcPositionsRef.current
      );

      const nextStates = new Map(statesRef.current);
      const anyAware = Array.from(nextStates.values()).some(state => state.aware || state.alert);
      const anyGlance = Array.from(nextStates.values()).some(state => state.glanceUntil > now);
      const ambientShift = anyGlance ? 0.055 : anyAware ? 0.03 : 0;

      setSnapshot({
        states: nextStates,
        anyAware,
        ambientShift,
        idleSeconds: idleRef.current,
      });
    }, UPDATE_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [map, paused]);

  return snapshot;
}

// ============================================================================
// Cold Zones
// ============================================================================

export function getColdZoneAt(map: LocalMapTemplate, position: Point): ColdZone | null {
  if (!map.coldZones || map.coldZones.length === 0) return null;

  const gridPos = worldToGrid(position.x, position.y);

  for (const zone of map.coldZones) {
    const { col, row, width, height } = zone.bounds;
    if (
      gridPos.col >= col &&
      gridPos.col < col + width &&
      gridPos.row >= row &&
      gridPos.row < row + height
    ) {
      return zone;
    }
  }

  return null;
}

// ============================================================================
// Internals
// ============================================================================

function updateNpcAwareness(
  map: LocalMapTemplate,
  playerPosition: Point,
  idleSeconds: number,
  nowMs: number,
  deltaSeconds: number,
  states: Map<string, AwarenessState>,
  npcPositions?: Map<string, Point>
) {
  const activeNpcIds = new Set<string>();

  for (const obj of map.objects) {
    if (obj.type !== 'npc') continue;
    activeNpcIds.add(obj.id);

    const npcData = obj.data as NPCObjectData | undefined;
    const simPos = npcPositions?.get(obj.id);
    const npcWorld = simPos || gridToWorld(obj.position.col, obj.position.row);
    const dist = euclideanDistance(playerPosition, npcWorld);
    const inRange = dist <= NPC_DETECTION_RANGE;
    const hasSight = inRange ? hasLineOfSight(map, npcWorld, playerPosition) : false;

    const state = states.get(obj.id) || createInitialAwarenessState(obj.id, nowMs, npcData);
    state.alert = npcData?.behaviorState === 'alert';

    if (inRange && hasSight) {
      state.proximitySeconds += deltaSeconds;
    } else {
      state.proximitySeconds = Math.max(0, state.proximitySeconds - deltaSeconds * 1.5);
    }

    state.aware = state.proximitySeconds >= AWARE_THRESHOLD_SECONDS;

    const lingerRange = Math.min(NPC_DETECTION_RANGE * 0.75, INTERACTION_RANGE * 1.4);
    if (state.aware && dist <= lingerRange && idleSeconds >= IDLE_LINGER_GATE_SECONDS) {
      state.lingerSeconds += deltaSeconds;
    } else {
      state.lingerSeconds = Math.max(0, state.lingerSeconds - deltaSeconds);
    }

    // Glance behavior
    if (state.aware && nowMs >= state.nextGlanceAt) {
      state.glanceUntil = nowMs + GLANCE_DURATION_MS;
      state.nextGlanceAt = nowMs + state.glanceIntervalMs;
    }

    if (nowMs <= state.glanceUntil) {
      state.facingOverride = facingToward(playerPosition, npcWorld);
    } else {
      state.facingOverride = undefined;
    }

    // Linger-driven shift
    const lingerThreshold = npcData?.lingerTimer ?? LINGER_THRESHOLD_SECONDS;
    if (
      state.aware &&
      state.lingerSeconds >= lingerThreshold &&
      nowMs - state.lastShiftAt > SHIFT_COOLDOWN_MS
    ) {
      state.shiftOffset = offsetAway(npcWorld, playerPosition, 3);
      state.shiftUntil = nowMs + SHIFT_DURATION_MS;
      state.lastShiftAt = nowMs;
    }

    // Flee on approach
    const fleeOnApproach = npcData?.fleeOnApproach === true;
    if (
      fleeOnApproach &&
      dist <= INTERACTION_RANGE * 0.8 &&
      hasSight &&
      nowMs - state.lastFleeAt > FLEE_COOLDOWN_MS
    ) {
      state.fleeOffset = offsetAway(npcWorld, playerPosition, 18);
      state.fleeUntil = nowMs + FLEE_DURATION_MS;
      state.lastFleeAt = nowMs;
    }

    if (nowMs > state.shiftUntil) {
      state.shiftOffset = { x: 0, y: 0 };
    }

    if (nowMs > state.fleeUntil) {
      state.fleeOffset = { x: 0, y: 0 };
    }

    state.positionOffset =
      nowMs <= state.fleeUntil
        ? state.fleeOffset
        : nowMs <= state.shiftUntil
        ? state.shiftOffset
        : { x: 0, y: 0 };

    states.set(obj.id, state);
  }

  // Cleanup states for NPCs no longer present
  for (const id of states.keys()) {
    if (!activeNpcIds.has(id)) {
      states.delete(id);
    }
  }
}

function createInitialAwarenessState(
  npcId: string,
  nowMs: number,
  npcData?: NPCObjectData
): AwarenessState {
  const glanceIntervalMs =
    (npcData?.glanceInterval ?? (2.8 + Math.random() * 1.8)) * 1000;

  return {
    npcId,
    aware: false,
    alert: false,
    proximitySeconds: 0,
    lingerSeconds: 0,
    glanceUntil: 0,
    nextGlanceAt: nowMs + glanceIntervalMs,
    glanceIntervalMs,
    shiftUntil: 0,
    shiftOffset: { x: 0, y: 0 },
    fleeUntil: 0,
    fleeOffset: { x: 0, y: 0 },
    lastShiftAt: 0,
    lastFleeAt: 0,
    positionOffset: { x: 0, y: 0 },
  };
}

function facingToward(
  target: Point,
  from: Point
): 'north' | 'south' | 'east' | 'west' {
  const dx = target.x - from.x;
  const dy = target.y - from.y;

  if (Math.abs(dx) > Math.abs(dy)) {
    return dx >= 0 ? 'east' : 'west';
  }
  return dy >= 0 ? 'south' : 'north';
}

function offsetAway(source: Point, from: Point, magnitude: number): Point {
  const dx = source.x - from.x;
  const dy = source.y - from.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;

  return {
    x: (dx / dist) * magnitude,
    y: (dy / dist) * magnitude,
  };
}
