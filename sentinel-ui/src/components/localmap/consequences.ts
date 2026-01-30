/**
 * Consequence System (Phase 6)
 *
 * Evaluates dormant threads, faction pressure, and consequence events
 * so the world shifts while the player is absent.
 */

import type { GridPosition, LocalMapTemplate, Point } from './types';
import { ENTITY_COLORS } from './types';

// ============================================================================
// Types
// ============================================================================

export type PressureDirection = 'rising' | 'falling' | 'stable';

export interface FactionPressure {
  factionId: string;
  level: number; // 0-100
  direction: PressureDirection;
  visualCue: string;
}

export interface ThreadSpatialData {
  mapId: string;
  position: GridPosition;
  radius?: number;
  marker?: 'signal' | 'fracture' | 'echo';
}

export interface DormantThread {
  id: string;
  description: string;
  triggerCondition: string;
  spatial: ThreadSpatialData;
  severity?: 'minor' | 'moderate' | 'major';
  createdAtMinutes?: number;
  factionId?: string;
}

export type ConsequenceEventType =
  | 'faction_shift'
  | 'npc_moved'
  | 'thread_surfaced'
  | 'hinge_locked'
  | 'combat_consequence';

export interface ConsequenceEvent {
  id: string;
  type: ConsequenceEventType;
  description: string;
  factionId?: string;
  npcId?: string;
  timestamp: number;
  mapId: string;
  position?: GridPosition;
  severity?: 'info' | 'warning' | 'critical';
}

export interface FactionPressureZone {
  id: string;
  factionId: string;
  level: number;
  direction: PressureDirection;
  bounds: {
    col: number;
    row: number;
    width: number;
    height: number;
  };
}

export type NotificationType = ConsequenceEventType;

export interface ConsequenceNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  factionId?: string;
  npcId?: string;
  mapId?: string;
  position?: GridPosition;
  timestamp: number;
  severity?: 'info' | 'warning' | 'critical';
}

export interface ConsequenceHighlight {
  id: string;
  mapId: string;
  position: GridPosition;
  createdAt: number;
  durationMs?: number;
  color?: string;
}

export interface ConsequenceContext {
  currentMapId: string;
  timeMinutes: number;
  playerPosition?: Point;
  factionPressures: FactionPressure[];
  visitedMaps: Map<string, { lastVisitedAt: number; visits: number }>;
}

export interface ThreadEvaluationResult {
  surfaced: DormantThread[];
  events: ConsequenceEvent[];
}

// ============================================================================
// Utilities
// ============================================================================

export function getFactionColor(factionId: string): string {
  const palette = Object.values(ENTITY_COLORS.npc);
  const index = Math.abs(hashString(factionId)) % palette.length;
  return palette[index] || ENTITY_COLORS.npc.neutral;
}

export function derivePressureDirection(previous: number | undefined, next: number): PressureDirection {
  if (typeof previous !== 'number') return 'stable';
  const delta = next - previous;
  if (delta >= 6) return 'rising';
  if (delta <= -6) return 'falling';
  return 'stable';
}

export function buildPressureZones(
  map: LocalMapTemplate,
  pressures: FactionPressure[]
): FactionPressureZone[] {
  const zones: FactionPressureZone[] = [];
  if (!map || pressures.length === 0) return zones;

  const sorted = [...pressures].sort((a, b) => b.level - a.level).slice(0, 3);

  for (const pressure of sorted) {
    const zoneCount = Math.max(1, Math.min(3, Math.round(pressure.level / 35)));
    for (let i = 0; i < zoneCount; i++) {
      const seed = hashString(`${map.id}:${pressure.factionId}:${i}`);
      const rand = seededRandom(seed);
      const width = Math.max(3, Math.min(map.width - 2, Math.round(3 + rand() * 6)));
      const height = Math.max(3, Math.min(map.height - 2, Math.round(3 + rand() * 6)));
      const col = Math.max(0, Math.min(map.width - width, Math.floor(rand() * map.width)));
      const row = Math.max(0, Math.min(map.height - height, Math.floor(rand() * map.height)));

      zones.push({
        id: `${pressure.factionId}-${i}`,
        factionId: pressure.factionId,
        level: pressure.level,
        direction: pressure.direction,
        bounds: { col, row, width, height },
      });
    }
  }

  return zones;
}

export function evaluateDormantThreads(
  threads: DormantThread[],
  context: ConsequenceContext
): ThreadEvaluationResult {
  const surfaced: DormantThread[] = [];
  const events: ConsequenceEvent[] = [];

  for (const thread of threads) {
    const mapId = thread.spatial?.mapId;
    if (!mapId) continue;

    const visit = context.visitedMaps.get(mapId);
    const revisited = visit ? visit.visits > 1 : false;
    const minutesSinceLastVisit = visit ? context.timeMinutes - visit.lastVisitedAt : 0;
    const minutesSinceCreated = thread.createdAtMinutes
      ? context.timeMinutes - thread.createdAtMinutes
      : minutesSinceLastVisit;

    const triggerText = thread.triggerCondition.toLowerCase();
    const highPressure = thread.factionId
      ? context.factionPressures.some(
          pressure => pressure.factionId === thread.factionId && pressure.level >= 70
        )
      : false;

    const shouldSurface =
      (mapId === context.currentMapId && revisited && minutesSinceLastVisit >= 8) ||
      (mapId === context.currentMapId && triggerText.includes('return')) ||
      (minutesSinceCreated >= 40 && mapId === context.currentMapId) ||
      (highPressure && mapId === context.currentMapId);

    if (!shouldSurface) continue;

    surfaced.push(thread);
    events.push({
      id: `thread-${thread.id}`,
      type: 'thread_surfaced',
      description: thread.description || thread.triggerCondition,
      factionId: thread.factionId,
      timestamp: Date.now(),
      mapId,
      position: thread.spatial?.position,
      severity: thread.severity === 'major' ? 'critical' : thread.severity === 'minor' ? 'info' : 'warning',
    });
  }

  return { surfaced, events };
}

export function evaluateFactionPressureEvents(
  pressures: FactionPressure[],
  context: ConsequenceContext
): ConsequenceEvent[] {
  const events: ConsequenceEvent[] = [];

  for (const pressure of pressures) {
    if (pressure.level < 72 || pressure.direction !== 'rising') continue;

    events.push({
      id: `pressure-${pressure.factionId}-${Math.floor(context.timeMinutes / 10)}`,
      type: 'faction_shift',
      description: `${pressure.factionId.replace(/_/g, ' ')} influence is tightening nearby.`,
      factionId: pressure.factionId,
      timestamp: Date.now(),
      mapId: context.currentMapId,
      severity: pressure.level >= 90 ? 'critical' : 'warning',
    });
  }

  return events;
}

export function ensureThreadSpatial(
  thread: DormantThread,
  map: LocalMapTemplate
): DormantThread {
  if (thread.spatial && thread.spatial.mapId && thread.spatial.position) return thread;

  const seed = hashString(`${map.id}:${thread.id}`);
  const rand = seededRandom(seed);
  const col = Math.max(0, Math.min(map.width - 1, Math.floor(rand() * map.width)));
  const row = Math.max(0, Math.min(map.height - 1, Math.floor(rand() * map.height)));

  return {
    ...thread,
    spatial: {
      mapId: map.id,
      position: { col, row },
      radius: 1,
      marker: 'echo',
    },
  };
}

// ============================================================================
// Internals
// ============================================================================

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

function seededRandom(seed: number): () => number {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
