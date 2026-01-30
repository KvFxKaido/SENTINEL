import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LocalMapTemplate, NPCObjectData, Point } from './types';
import type { GameTime } from './useGameClock';
import { timeToMinutes } from './useGameClock';
import type {
  ConsequenceContext,
  ConsequenceEvent,
  ConsequenceEventType,
  ConsequenceNotification,
  DormantThread,
  FactionPressure,
  FactionPressureZone,
} from './consequences';
import {
  buildPressureZones,
  derivePressureDirection,
  ensureThreadSpatial,
  evaluateDormantThreads,
  evaluateFactionPressureEvents,
} from './consequences';
import { getConsequences, acknowledgeNotification } from '../../lib/gameApi';
import { gridToWorld, euclideanDistance } from './collision';

// ============================================================================
// Types
// ============================================================================

export interface UseConsequencesOptions {
  map: LocalMapTemplate | null;
  mapId: string;
  campaignId: string;
  playerPosition: Point;
  gameTime: GameTime;
  paused?: boolean;
}

export interface ConsequenceState {
  pressures: FactionPressure[];
  pressureZones: FactionPressureZone[];
  dormantThreads: DormantThread[];
  events: ConsequenceEvent[];
  notifications: ConsequenceNotification[];
  npcDispositionOverrides: Map<string, string>;
  dismissNotification: (id: string) => void;
}

// ============================================================================
// Hook
// ============================================================================

const POLL_INTERVAL_MS = 4500;
const OFFSCREEN_DISTANCE = 180;

export function useConsequences({
  map,
  mapId,
  campaignId,
  playerPosition,
  gameTime,
  paused = false,
}: UseConsequencesOptions): ConsequenceState {
  const [pressures, setPressures] = useState<FactionPressure[]>([]);
  const [pressureZones, setPressureZones] = useState<FactionPressureZone[]>([]);
  const [dormantThreads, setDormantThreads] = useState<DormantThread[]>([]);
  const [events, setEvents] = useState<ConsequenceEvent[]>([]);
  const [notifications, setNotifications] = useState<ConsequenceNotification[]>([]);

  const previousPressureRef = useRef<Map<string, number>>(new Map());
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const visitedMapsRef = useRef<Map<string, { lastVisitedAt: number; visits: number }>>(new Map());
  const lastMapIdRef = useRef<string | null>(null);

  const totalMinutes = useMemo(() => timeToMinutes(gameTime), [gameTime]);

  useEffect(() => {
    if (!mapId) return;
    if (lastMapIdRef.current === mapId) return;

    const record = visitedMapsRef.current.get(mapId);
    if (record) {
      record.visits += 1;
      record.lastVisitedAt = totalMinutes;
    } else {
      visitedMapsRef.current.set(mapId, { lastVisitedAt: totalMinutes, visits: 1 });
    }
    lastMapIdRef.current = mapId;
  }, [mapId, totalMinutes]);

  useEffect(() => {
    if (!mapId) return;
    const record = visitedMapsRef.current.get(mapId);
    if (record) {
      record.lastVisitedAt = totalMinutes;
    }
  }, [mapId, totalMinutes]);

  const mapThreadsToSpatial = useCallback((threads: DormantThread[]) => {
    if (!map) return threads;
    return threads.map(thread => ensureThreadSpatial(thread, map));
  }, [map]);

  const updateNpcDispositions = useCallback((nextPressures: FactionPressure[]) => {
    const overrides = new Map<string, string>();
    if (!map) return overrides;

    for (const obj of map.objects) {
      if (obj.type !== 'npc') continue;
      const data = obj.data as NPCObjectData | undefined;
      if (!data?.faction) continue;
      const pressure = nextPressures.find(p => p.factionId === data.faction);
      if (!pressure) continue;

      let nextDisposition = data.disposition || 'neutral';
      if (pressure.level >= 80 && pressure.direction === 'rising') {
        nextDisposition = 'hostile';
      } else if (pressure.level >= 60 && pressure.direction === 'rising') {
        nextDisposition = 'wary';
      } else if (pressure.level <= 30 && pressure.direction === 'falling') {
        nextDisposition = 'warm';
      }

      if (nextDisposition !== data.disposition) {
        overrides.set(obj.id, nextDisposition);
      }
    }

    return overrides;
  }, [map]);

  const addNotifications = useCallback((incoming: ConsequenceNotification[]) => {
    if (incoming.length === 0) return;
    setNotifications(prev => {
      const combined = [...incoming, ...prev];
      return combined.slice(0, 3);
    });
  }, []);

  const dismissNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
    acknowledgeNotification(id);
  }, []);

  useEffect(() => {
    if (paused) return;
    let active = true;
    let intervalId: number | null = null;

    const poll = async () => {
      if (!active) return;
      if (!mapId) return;

      const response = await getConsequences(mapId, campaignId);
      if (!active || !response.ok) return;

      const nextPressures: FactionPressure[] = (response.pressures || []).map(pressure => {
        const previous = previousPressureRef.current.get(pressure.faction_id);
        const rawLevel = typeof pressure.level === 'number' ? pressure.level : 0;
        const level = Math.max(0, Math.min(100, rawLevel));
        const direction = derivePressureDirection(previous, level);
        previousPressureRef.current.set(pressure.faction_id, level);
        return {
          factionId: pressure.faction_id,
          level,
          direction,
          visualCue: direction === 'rising' ? 'pulse' : direction === 'falling' ? 'fade' : 'steady',
        };
      });

      const mappedThreads: DormantThread[] = (response.pending_threads || []).map(thread => ({
        id: thread.id,
        description: thread.description || thread.trigger,
        triggerCondition: thread.trigger,
        severity: thread.severity as DormantThread['severity'],
        createdAtMinutes: typeof thread.created_minutes === 'number' ? thread.created_minutes : undefined,
        factionId: thread.faction_id,
        spatial: normalizeThreadSpatial(thread, map?.id || mapId),
      }));

      const spatialThreads = mapThreadsToSpatial(mappedThreads);
      const context: ConsequenceContext = {
        currentMapId: map?.id || mapId,
        timeMinutes: totalMinutes,
        playerPosition,
        factionPressures: nextPressures,
        visitedMaps: visitedMapsRef.current,
      };
      const threadEvaluation = evaluateDormantThreads(spatialThreads, context);
      const pressureEvents = evaluateFactionPressureEvents(nextPressures, context);

      const apiEvents: ConsequenceEvent[] = (response.recent_activations || []).map(event => ({
        id: event.id,
        type: (event.type || 'thread_surfaced') as ConsequenceEventType,
        description: event.description || event.headline || 'Consequences ripple through the city.',
        factionId: event.faction_id,
        npcId: event.npc_id,
        timestamp: event.timestamp || Date.now(),
        mapId: event.map_id || map?.id || mapId,
        position: event.position,
        severity: event.severity,
      }));

      const nextEvents = [...pressureEvents, ...threadEvaluation.events, ...apiEvents]
        .filter(event => {
          if (seenEventIdsRef.current.has(event.id)) return false;
          seenEventIdsRef.current.add(event.id);
          return true;
        });

      const offscreenNotifications = nextEvents
        .filter(event => isEventOffscreen(event, map?.id || mapId, playerPosition))
        .map(event => eventToNotification(event));

      if (offscreenNotifications.length > 0) {
        addNotifications(offscreenNotifications);
      }

      setPressures(nextPressures);
      setPressureZones(map ? buildPressureZones(map, nextPressures) : []);
      setDormantThreads(spatialThreads);
      setEvents(prev => [...nextEvents, ...prev].slice(0, 15));
    };

    poll();
    intervalId = window.setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      active = false;
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [
    paused,
    mapId,
    campaignId,
    map,
    playerPosition,
    totalMinutes,
    mapThreadsToSpatial,
    addNotifications,
    updateNpcDispositions,
  ]);

  const npcDispositionOverrides = useMemo(
    () => updateNpcDispositions(pressures),
    [pressures, updateNpcDispositions]
  );

  return {
    pressures,
    pressureZones,
    dormantThreads,
    events,
    notifications,
    npcDispositionOverrides,
    dismissNotification,
  };
}

// ============================================================================
// Helpers
// ============================================================================

function isEventOffscreen(
  event: ConsequenceEvent,
  currentMapId: string,
  playerPosition: Point
): boolean {
  if (event.mapId && event.mapId !== currentMapId) return true;
  if (!event.position) return false;

  const worldPos = gridToWorld(event.position.col, event.position.row);
  return euclideanDistance(playerPosition, worldPos) > OFFSCREEN_DISTANCE;
}

function normalizeThreadSpatial(
  thread: { spatial?: any },
  fallbackMapId: string
): DormantThread['spatial'] {
  const spatial = thread.spatial;
  if (spatial) {
    if (spatial.position && typeof spatial.position.col === 'number') {
      return {
        mapId: spatial.mapId || spatial.map_id || fallbackMapId,
        position: spatial.position,
        marker: spatial.marker || 'echo',
      };
    }
    if (typeof spatial.col === 'number' && typeof spatial.row === 'number') {
      return {
        mapId: spatial.mapId || spatial.map_id || fallbackMapId,
        position: { col: spatial.col, row: spatial.row },
        marker: spatial.marker || 'echo',
      };
    }
  }

  return {
    mapId: fallbackMapId,
    position: { col: 0, row: 0 },
    marker: 'echo',
  };
}

function eventToNotification(event: ConsequenceEvent): ConsequenceNotification {
  const title = event.type.replace(/_/g, ' ').toUpperCase();
  return {
    id: event.id,
    type: event.type,
    title,
    message: event.description,
    factionId: event.factionId,
    npcId: event.npcId,
    mapId: event.mapId,
    position: event.position,
    timestamp: event.timestamp,
    severity: event.severity,
  };
}
