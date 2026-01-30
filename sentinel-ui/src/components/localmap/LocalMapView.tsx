/**
 * LocalMapView — Main local map component (Phase 2)
 * 
 * Wraps LocalMapCanvas with state management, interaction panels,
 * and map transitions.
 * 
 * This is the primary exploration interface for Phase 2.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { LocalMapCanvas } from './LocalMapCanvas';
import { DialogueOverlay } from './DialogueOverlay';
import { getMapTemplate, getSpawnPoint } from './maps';
import { gridToWorld } from './collision';
import { getColdZoneAt, useNpcAwareness } from './awareness';
import { useGameClock, formatTimeShort, getTimeOfDay } from './useGameClock';
import { usePatrolSimulation } from './usePatrolSimulation';
import { useCombat } from './useCombat';
import { useConsequences } from './useConsequences';
import { NotificationSystem } from './NotificationSystem';
import { CombatOverlay } from './CombatOverlay';
import { startDialogue, continueDialogue, getState } from '../../lib/gameApi';
import { useAudio } from './useAudio'; // Import Audio Hook
import type { 
  LocalMapTemplate, 
  MapObject, 
  MapExit, 
  Point, 
  GridPosition,
  NPCObjectData,
} from './types';
import { TileType, INTERACTION_RANGE } from './types';
import type { ConsequenceHighlight, ConsequenceNotification } from './consequences';
import type { CombatEndResult, DialogueOption, DialogueResponse, SocialEnergyState } from '../../lib/gameApi';
import { CombatState } from './combat';
import './localmap.css';

// ============================================================================
// Types
// ============================================================================

interface LocalMapViewProps {
  initialMapId: string;
  initialSpawnId?: string;
  initialTime?: { day: number; hour: number; minute: number };
  onMapChange?: (mapId: string) => void;
  onInteraction?: (type: string, target: MapObject | MapExit) => void;
  onTimeChange?: (time: { day: number; hour: number; minute: number }) => void;
  onExit?: () => void;
}

interface InteractionPanelProps {
  target: MapObject | MapExit | null;
  type: 'object' | 'exit' | null;
  onAction: (action: string, params?: Record<string, unknown>) => void;
  onClose: () => void;
  playInteraction: (type: 'hover' | 'select' | 'alert' | 'cancel') => void; // Add audio prop
}

interface DialogueSession {
  npcId: string;
  npcName: string;
  npcFaction: string | null;
  npcDisposition: string;
}

const EMPTY_MAP: LocalMapTemplate = {
  id: 'empty',
  name: 'Empty',
  regionId: 'none',
  description: 'Placeholder map.',
  width: 1,
  height: 1,
  tileSize: 32,
  tiles: [[TileType.FLOOR]],
  objects: [],
  exits: [],
  spawnPoints: [
    {
      id: 'default',
      position: { col: 0, row: 0 },
      facing: 'south',
      isDefault: true,
    },
  ],
  ambientLight: 0.2,
  atmosphere: 'neutral',
};

// ============================================================================
// Interaction Panel Component
// ============================================================================

function InteractionPanel({ target, type, onAction, onClose, playInteraction }: InteractionPanelProps) {
  if (!target) {
    return (
      <div className="localmap-panel localmap-panel-empty">
        <div className="panel-empty-content">
          <div className="panel-empty-icon">◆</div>
          <p className="panel-empty-hint">
            Move with WASD or arrow keys.<br />
            Press E to interact with nearby objects.
          </p>
          <div className="panel-controls">
            <div className="control-row">
              <span className="control-key">WASD</span>
              <span className="control-action">Move</span>
            </div>
            <div className="control-row">
              <span className="control-key">E</span>
              <span className="control-action">Interact</span>
            </div>
            <div className="control-row">
              <span className="control-key">ESC</span>
              <span className="control-action">Menu</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isExit = type === 'exit';
  const exit = isExit ? (target as MapExit) : null;
  const obj = !isExit ? (target as MapObject) : null;

  const handleAction = (action: string, params?: any) => {
    playInteraction('select');
    onAction(action, params);
  };

  const handleClose = () => {
    playInteraction('cancel');
    onClose();
  };

  return (
    <div className="localmap-panel">
      <div className="panel-header">
        <h3 className="panel-title">
          {isExit ? exit?.label : obj?.name}
        </h3>
        <button className="panel-close" onClick={handleClose} onMouseEnter={() => playInteraction('hover')}>×</button>
      </div>
      
      <div className="panel-content">
        {isExit && exit && (
          <>
            <p className="panel-description">
              {exit.locked 
                ? `This exit is locked: ${exit.lockReason}`
                : `Travel to ${exit.label}`
              }
            </p>
            {!exit.locked && (
              <div className="panel-actions">
                <button 
                  className="action-button action-primary"
                  onClick={() => handleAction('travel', { exitId: exit.id })}
                  onMouseEnter={() => playInteraction('hover')}
                >
                  Enter
                </button>
              </div>
            )}
            {exit.locked && exit.requiresKey && (
              <p className="panel-hint">Requires: {exit.requiresKey}</p>
            )}
          </>
        )}
        
        {obj && obj.type === 'npc' && (
          <>
            <div className="panel-npc-info">
              {obj.data && (
                <>
                  {(obj.data as { faction?: string }).faction && (
                    <span className="npc-faction">
                      {(obj.data as { faction: string }).faction.replace(/_/g, ' ')}
                    </span>
                  )}
                  <span className={`npc-disposition disposition-${(obj.data as { disposition?: string }).disposition || 'neutral'}`}>
                    {(obj.data as { disposition?: string }).disposition || 'neutral'}
                  </span>
                </>
              )}
            </div>
            <div className="panel-actions">
              <button 
                className="action-button action-primary"
                onClick={() => handleAction('talk', { npcId: (obj.data as { npcId?: string })?.npcId })}
                onMouseEnter={() => playInteraction('hover')}
              >
                Talk
              </button>
              <button 
                className="action-button action-secondary"
                onClick={() => handleAction('observe', { objectId: obj.id })}
                onMouseEnter={() => playInteraction('hover')}
              >
                Observe
              </button>
            </div>
          </>
        )}
        
        {obj && obj.type === 'prop' && (
          <>
            <p className="panel-description">
              {(obj.data as { propType?: string })?.propType === 'container' 
                ? 'A storage container. Might contain useful items.'
                : (obj.data as { propType?: string })?.propType === 'terminal'
                ? 'A computer terminal. Could have valuable information.'
                : 'An object of interest.'}
            </p>
            <div className="panel-actions">
              {(obj.data as { interactable?: boolean })?.interactable && (
                <button 
                  className="action-button action-primary"
                  onClick={() => handleAction('use', { objectId: obj.id })}
                  onMouseEnter={() => playInteraction('hover')}
                >
                  {(obj.data as { propType?: string })?.propType === 'container' ? 'Open' : 'Use'}
                </button>
              )}
              <button 
                className="action-button action-secondary"
                onClick={() => handleAction('examine', { objectId: obj.id })}
                onMouseEnter={() => playInteraction('hover')}
              >
                Examine
              </button>
            </div>
          </>
        )}
        
        {obj && obj.type === 'item' && (
          <>
            <p className="panel-description">
              {(obj.data as { hidden?: boolean })?.hidden 
                ? 'Something is hidden here.'
                : 'An item on the ground.'}
            </p>
            <div className="panel-actions">
              <button 
                className="action-button action-primary"
                onClick={() => handleAction('pickup', { itemId: (obj.data as { itemId?: string })?.itemId })}
                onMouseEnter={() => playInteraction('hover')}
              >
                Pick Up
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Map Transition Component
// ============================================================================

interface MapTransitionProps {
  fromMap: string;
  toMap: string;
  direction: string;
  onComplete: () => void;
}

function MapTransition({ fromMap, toMap, direction, onComplete }: MapTransitionProps) {
  useEffect(() => {
    const timer = setTimeout(onComplete, 800);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="map-transition">
      <div className={`transition-overlay transition-${direction}`}>
        <div className="transition-text">
          <span className="transition-arrow">
            {direction === 'north' ? '↑' : direction === 'south' ? '↓' : direction === 'east' ? '→' : '←'}
          </span>
          <span className="transition-label">ENTERING</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

const DISPOSITION_ORDER = ['hostile', 'wary', 'neutral', 'warm', 'loyal'] as const;

function shiftDisposition(current: string, delta: number): string {
  const normalized = current || 'neutral';
  const startIndex = DISPOSITION_ORDER.indexOf(normalized as typeof DISPOSITION_ORDER[number]);
  const baseIndex = startIndex >= 0 ? startIndex : DISPOSITION_ORDER.indexOf('neutral');
  const nextIndex = Math.min(
    DISPOSITION_ORDER.length - 1,
    Math.max(0, baseIndex + Math.round(delta))
  );
  return DISPOSITION_ORDER[nextIndex];
}

export function LocalMapView({
  initialMapId,
  initialSpawnId,
  initialTime = { day: 0, hour: 8, minute: 0 },
  onMapChange,
  onInteraction,
  onTimeChange,
  onExit,
}: LocalMapViewProps) {
  const [currentMapId, setCurrentMapId] = useState(initialMapId);
  const [currentMap, setCurrentMap] = useState<LocalMapTemplate | null>(
    () => getMapTemplate(initialMapId)
  );
  const [spawnPosition, setSpawnPosition] = useState<Point | null>(() => {
    const spawn = getSpawnPoint(initialMapId, initialSpawnId || 'default');
    return spawn ? gridToWorld(spawn.col, spawn.row) : null;
  });
  const [spawnFacing, setSpawnFacing] = useState<'north' | 'south' | 'east' | 'west'>(() => {
    const spawn = getSpawnPoint(initialMapId, initialSpawnId || 'default');
    return (spawn?.facing as 'north' | 'south' | 'east' | 'west') || 'south';
  });
  
  const [selectedTarget, setSelectedTarget] = useState<MapObject | MapExit | null>(null);
  const [selectedType, setSelectedType] = useState<'object' | 'exit' | null>(null);
  const [paused, setPaused] = useState(false);
  const [combatPaused, setCombatPaused] = useState(false);

  const [campaignId, setCampaignId] = useState<string>('');
  const [dialogueSession, setDialogueSession] = useState<DialogueSession | null>(null);
  const [dialogueResponse, setDialogueResponse] = useState<DialogueResponse | null>(null);
  const [dialogueLoading, setDialogueLoading] = useState(false);
  const [dialogueError, setDialogueError] = useState<string | null>(null);
  const [dialogueSpentMinutes, setDialogueSpentMinutes] = useState(0);
  const [dialogueDispositionDelta, setDialogueDispositionDelta] = useState(0);
  const [socialEnergy, setSocialEnergy] = useState<SocialEnergyState | null>(null);
  const dialogueRequestRef = useRef(0);
  const dialogueClosingRef = useRef(false);

  // Audio Hook
  const audio = useAudio();
  const { playInteraction } = audio;

  const dialogueActive = !!dialogueSession;
  
  // Game clock - pauses during interactions and transitions
  const [clockState, clockActions] = useGameClock({
    initialTime,
    autoAdvance: true,
    onTimeChange: (time) => onTimeChange?.(time),
  });
  const { advanceTime } = clockActions;
  

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const queryCampaign = params.get('campaign') || params.get('campaignId');
    const globalCampaign = (window as any).currentCampaignId as string | undefined;
    setCampaignId(queryCampaign || globalCampaign || '');
  }, []);

  useEffect(() => {
    let active = true;
    getState().then((state) => {
      if (!active) return;
      if (state.ok && state.character?.social_energy) {
        setSocialEnergy(state.character.social_energy);
      }
    });
    return () => {
      active = false;
    };
  }, []);
  
  const [transition, setTransition] = useState<{
    from: string;
    to: string;
    direction: string;
    targetSpawn: string;
  } | null>(null);
  
  const [playerGridPos, setPlayerGridPos] = useState<GridPosition>(() => {
    const spawn = getSpawnPoint(initialMapId, initialSpawnId || 'default');
    return spawn ? { col: spawn.col, row: spawn.row } : { col: 0, row: 0 };
  });
  const [currentPlayerPos, setCurrentPlayerPos] = useState<Point>(() => {
    const spawn = getSpawnPoint(initialMapId, initialSpawnId || 'default');
    return spawn ? gridToWorld(spawn.col, spawn.row) : { x: 0, y: 0 };
  });
  const [idleSeconds, setIdleSeconds] = useState(0);
  const [mapHighlight, setMapHighlight] = useState<ConsequenceHighlight | null>(null);
  const [, setFactionStanding] = useState<Map<string, number>>(new Map());
  const observedConsequencesRef = useRef<Set<string>>(new Set());
  const missedConsequencesRef = useRef<Set<string>>(new Set());
  
  const containerRef = useRef<HTMLDivElement>(null);

  // Fallback: if requested map doesn't exist, redirect to safehouse
  useEffect(() => {
    if (!currentMap && currentMapId !== 'safehouse_main') {
      const fallback = getMapTemplate('safehouse_main');
      if (fallback) {
        const timer = setTimeout(() => {
          setCurrentMapId('safehouse_main');
          setCurrentMap(fallback);
          const spawn = getSpawnPoint('safehouse_main', 'default');
          if (spawn) {
            const worldPos = gridToWorld(spawn.col, spawn.row);
            setSpawnPosition(worldPos);
            setSpawnFacing((spawn.facing as 'north' | 'south' | 'east' | 'west') || 'south');
            setCurrentPlayerPos(worldPos);
          }
        }, 1200);
        return () => clearTimeout(timer);
      }
    }
  }, [currentMap, currentMapId]);

  // Load map on ID change
  useEffect(() => {
    const map = getMapTemplate(currentMapId);
    if (map) {
      setCurrentMap(map);

      // Get spawn position
      const spawn = getSpawnPoint(currentMapId, initialSpawnId || 'default');
      if (spawn) {
        const worldPos = gridToWorld(spawn.col, spawn.row);
        setSpawnPosition(worldPos);
        setSpawnFacing(spawn.facing as typeof spawnFacing);
        setCurrentPlayerPos(worldPos); // Initialize player pos for sim
        setIdleSeconds(0);
      }
      
      onMapChange?.(currentMapId);
    }
  }, [currentMapId, initialSpawnId, onMapChange]);

  // Patrol Simulation
  const npcStates = usePatrolSimulation(
    currentMap || { objects: [] } as any, // Dummy fallback if null, useEffect handles null map
    currentPlayerPos,
    clockState.time,
    !!(paused || transition || selectedTarget || dialogueActive || combatPaused)
  );
  const npcPositions = useMemo(() => {
    const positions = new Map<string, Point>();
    npcStates.forEach((state, id) => {
      positions.set(id, state.position);
    });
    return positions;
  }, [npcStates]);

  const mapForAwareness = currentMap || getMapTemplate(currentMapId) || EMPTY_MAP;

  const handleCombatEnd = useCallback((result: CombatEndResult) => {
    if (!result?.faction_impact) return;

    setFactionStanding(prev => {
      const next = new Map(prev);
      Object.entries(result.faction_impact || {}).forEach(([faction, delta]) => {
        if (typeof delta !== 'number' || delta === 0) return;
        next.set(faction, (next.get(faction) || 0) + delta);
      });
      return next;
    });

    setCurrentMap(prev => {
      if (!prev) return prev;
      let changed = false;
      const updatedObjects = prev.objects.map(obj => {
        if (obj.type !== 'npc') return obj;
        const data = obj.data as NPCObjectData | undefined;
        const faction = data?.faction;
        if (!faction) return obj;
        const delta = result.faction_impact?.[faction] || 0;
        if (delta === 0) return obj;
        const nextDisposition = shiftDisposition(data?.disposition || 'neutral', Math.sign(delta));
        if (nextDisposition === data?.disposition) return obj;
        changed = true;
        return {
          ...obj,
          data: {
            ...(data || { npcId: obj.id, faction, disposition: nextDisposition }),
            disposition: nextDisposition,
          } as NPCObjectData,
        };
      });
      return changed ? { ...prev, objects: updatedObjects } : prev;
    });
  }, []);

  const combat = useCombat({
    map: currentMap || mapForAwareness,
    npcStates,
    playerPosition: currentPlayerPos,
    playerFacing: spawnFacing,
    paused: !!(paused || transition || selectedTarget || dialogueActive),
    onCombatEnd: handleCombatEnd,
  });
  const combatActive = combat.active;
  const clearCombat = combat.actions.clearCombat;
  const clearCombatSelection = combat.actions.clearSelection;

  useEffect(() => {
    setCombatPaused(combatActive);
  }, [combatActive]);

  // Pause clock when interacting, in dialogue, combat, or paused
  useEffect(() => {
    if (paused || selectedTarget || dialogueActive || combatActive) {
      const reason = paused
        ? 'menu'
        : dialogueActive
        ? 'dialogue'
        : combatActive
        ? 'combat'
        : 'interaction';
      clockActions.pause(reason);
    } else {
      clockActions.resume();
    }
  }, [paused, selectedTarget, dialogueActive, combatActive, clockActions]);

  const awarenessSnapshot = useNpcAwareness({
    map: mapForAwareness,
    playerPosition: currentPlayerPos,
    paused: !!(paused || transition || selectedTarget || dialogueActive || combatActive),
    idleSeconds,
    npcPositions,
  });

  const consequenceState = useConsequences({
    map: currentMap || mapForAwareness,
    mapId: currentMapId,
    campaignId,
    playerPosition: currentPlayerPos,
    gameTime: clockState.time,
    paused: !!(paused || transition || selectedTarget || dialogueActive || combatActive),
  });

  const {
    pressures: factionPressures,
    pressureZones,
    dormantThreads,
    events: consequenceEvents,
    notifications: consequenceNotifications,
    npcDispositionOverrides,
    dismissNotification,
  } = consequenceState;

  const coldZone = getColdZoneAt(mapForAwareness, currentPlayerPos);
  const suppressPrompts = !!coldZone?.suppressPrompts;
  const suppressPanels = suppressPrompts || !!coldZone?.suppressDialogue || combatActive;

  useEffect(() => {
    if (!suppressPanels) return;
    if (selectedTarget || selectedType) {
      setSelectedTarget(null);
      setSelectedType(null);
    }
  }, [suppressPanels, selectedTarget, selectedType]);

  useEffect(() => {
    if (!currentMap) return;
    if (npcDispositionOverrides.size === 0) return;

    setCurrentMap(prev => {
      if (!prev) return prev;
      let changed = false;
      const updatedObjects = prev.objects.map(obj => {
        if (obj.type !== 'npc') return obj;
        const nextDisposition = npcDispositionOverrides.get(obj.id);
        if (!nextDisposition) return obj;
        const data = obj.data as NPCObjectData | undefined;
        if (data?.disposition === nextDisposition) return obj;
        changed = true;
        return {
          ...obj,
          data: {
            ...(data || { npcId: obj.id, faction: null, disposition: nextDisposition }),
            disposition: nextDisposition,
          } as NPCObjectData,
        };
      });
      return changed ? { ...prev, objects: updatedObjects } : prev;
    });
  }, [currentMap, npcDispositionOverrides]);

  useEffect(() => {
    setMapHighlight(null);
  }, [currentMapId]);

  useEffect(() => {
    if (consequenceEvents.length === 0) return;

    const nextObserved = new Set(observedConsequencesRef.current);
    const nextMissed = new Set(missedConsequencesRef.current);
    let observedChanged = false;
    let missedChanged = false;

    for (const event of consequenceEvents) {
      if (nextObserved.has(event.id) || nextMissed.has(event.id)) continue;

      const observed = event.mapId === currentMapId && (!event.position || (() => {
        const worldPos = gridToWorld(event.position.col, event.position.row);
        const dist = Math.hypot(worldPos.x - currentPlayerPos.x, worldPos.y - currentPlayerPos.y);
        return dist <= INTERACTION_RANGE;
      })());

      if (observed) {
        nextObserved.add(event.id);
        observedChanged = true;
      } else {
        nextMissed.add(event.id);
        missedChanged = true;
      }
    }

    if (observedChanged) {
      observedConsequencesRef.current = nextObserved;
    }
    if (missedChanged) {
      missedConsequencesRef.current = nextMissed;
    }
  }, [consequenceEvents, currentMapId, currentPlayerPos]);

  useEffect(() => {
    if (!mapHighlight) return;
    const duration = mapHighlight.durationMs ?? 2400;
    const timer = window.setTimeout(() => {
      setMapHighlight(null);
    }, duration);
    return () => window.clearTimeout(timer);
  }, [mapHighlight]);

  useEffect(() => {
    if (clockState.paused || paused || transition || dialogueActive || combatActive) return;

    const idleActive = idleSeconds >= 5;
    const awarenessActive = awarenessSnapshot.anyAware;
    if (!idleActive && !awarenessActive) return;

    const intervalMs = awarenessActive && idleActive ? 1500 : awarenessActive ? 2000 : 3200;
    const intervalId = window.setInterval(() => {
      advanceTime(1);
    }, intervalMs);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [
    clockState.paused,
    paused,
    transition,
    dialogueActive,
    combatActive,
    idleSeconds,
    awarenessSnapshot.anyAware,
    advanceTime,
  ]);

  // Handle exit approach
  const handleExitApproach = useCallback((exit: MapExit) => {
    if (suppressPrompts || dialogueActive || combatActive) return;
    setSelectedTarget(exit);
    setSelectedType('exit');
  }, [suppressPrompts, dialogueActive, combatActive]);

  // Handle object interaction
  const handleObjectInteract = useCallback((obj: MapObject) => {
    if (suppressPrompts || dialogueActive || combatActive) return;
    setSelectedTarget(obj);
    setSelectedType('object');
    onInteraction?.('select', obj);
  }, [suppressPrompts, dialogueActive, combatActive, onInteraction]);

  // Handle position change
  const handlePositionChange = useCallback((pos: Point, gridPos: GridPosition) => {
    setPlayerGridPos(gridPos);
    setCurrentPlayerPos(pos);
  }, []);

  const handleNotificationHighlight = useCallback((notification: ConsequenceNotification) => {
    dismissNotification(notification.id);
    if (notification.mapId && notification.mapId !== currentMapId) return;
    if (!notification.position) return;

    const color = notification.severity === 'critical'
      ? '248, 81, 73'
      : notification.severity === 'warning'
      ? '210, 153, 34'
      : '88, 166, 255';

    setMapHighlight({
      id: notification.id,
      mapId: notification.mapId || currentMapId,
      position: notification.position,
      createdAt: performance.now(),
      durationMs: 2200,
      color,
    });
  }, [currentMapId, dismissNotification]);

  const applyDialogueResponse = useCallback((response: DialogueResponse, optionCost?: number) => {
    setDialogueResponse(response);
    setDialogueError(response.error ?? null);
    setDialogueLoading(false);

    if (typeof response.disposition_change === 'number') {
      const delta = response.disposition_change;
      setDialogueDispositionDelta(prev => prev + delta);
    }

    const responseCost = typeof response.social_energy_cost === 'number' ? response.social_energy_cost : 0;
    const cost = responseCost !== 0
      ? responseCost
      : response.meta?.mock && optionCost
        ? optionCost
        : responseCost;

    if (cost > 0) {
      setDialogueSpentMinutes(prev => prev + cost);
      setSocialEnergy(prev => {
        if (!prev) return prev;
        const nextCurrent = Math.max(0, prev.current - cost);
        const percentage = prev.max > 0 ? (nextCurrent / prev.max) * 100 : prev.percentage;
        return { ...prev, current: nextCurrent, percentage };
      });
    }

    if (response.social_energy) {
      setSocialEnergy(response.social_energy);
    }
  }, []);

  const startDialogueSession = useCallback(async (npc: MapObject) => {
    const npcData = npc.data as NPCObjectData | undefined;
    const npcId = npcData?.npcId || npc.id;
    const npcName = npc.name || 'Unknown';
    const npcFaction = npcData?.faction || null;
    const npcDisposition = npcData?.disposition || 'neutral';

    dialogueClosingRef.current = false;
    setDialogueSession({ npcId, npcName, npcFaction, npcDisposition });
    setDialogueResponse(null);
    setDialogueError(null);
    setDialogueLoading(true);
    setDialogueSpentMinutes(0);
    setDialogueDispositionDelta(0);

    setSelectedTarget(null);
    setSelectedType(null);

    onInteraction?.('talk', npc);

    getState().then((state) => {
      if (state.ok && state.character?.social_energy) {
        setSocialEnergy(state.character.social_energy);
      }
    });

    const requestId = ++dialogueRequestRef.current;
    const response = await startDialogue(npcId, campaignId);
    if (dialogueRequestRef.current !== requestId) return;
    applyDialogueResponse(response);
  }, [campaignId, onInteraction, applyDialogueResponse]);

  const handleDialogueOption = useCallback(async (option: DialogueOption) => {
    if (!dialogueSession) return;
    
    playInteraction('select'); // Sound

    setDialogueLoading(true);
    const requestId = ++dialogueRequestRef.current;
    const response = await continueDialogue(dialogueSession.npcId, option.id, option.text);
    if (dialogueRequestRef.current !== requestId) return;
    applyDialogueResponse(response, option.social_cost);
  }, [dialogueSession, applyDialogueResponse, playInteraction]);

  const closeDialogue = useCallback(() => {
    if (dialogueClosingRef.current) return;
    playInteraction('cancel'); // Sound
    
    dialogueClosingRef.current = true;
    dialogueRequestRef.current += 1;

    if (dialogueSession && dialogueDispositionDelta !== 0) {
      const updatedDisposition = shiftDisposition(dialogueSession.npcDisposition, dialogueDispositionDelta);
      setCurrentMap(prev => {
        if (!prev) return prev;
        const updatedObjects = prev.objects.map(obj => {
          if (obj.type !== 'npc') return obj;
          const data = obj.data as NPCObjectData | undefined;
          const objNpcId = data?.npcId || obj.id;
          if (objNpcId !== dialogueSession.npcId) return obj;
          const fallbackData: NPCObjectData = {
            npcId: objNpcId,
            faction: data?.faction ?? null,
            disposition: updatedDisposition,
          };
          return {
            ...obj,
            data: {
              ...fallbackData,
              ...(data || {}),
              disposition: updatedDisposition,
            } as NPCObjectData,
          };
        });
        return { ...prev, objects: updatedObjects };
      });
    }

    if (dialogueSpentMinutes > 0) {
      clockActions.advanceTime(dialogueSpentMinutes);
    }

    setDialogueSession(null);
    setDialogueResponse(null);
    setDialogueError(null);
    setDialogueLoading(false);
    setDialogueSpentMinutes(0);
    setDialogueDispositionDelta(0);
  }, [dialogueSession, dialogueDispositionDelta, dialogueSpentMinutes, clockActions, playInteraction]);

  // Handle panel action
  const handleAction = useCallback((action: string, _params?: Record<string, unknown>) => {
    if (action === 'travel' && selectedTarget && selectedType === 'exit') {
      const exit = selectedTarget as MapExit;
      
      // Start transition
      setTransition({
        from: currentMapId,
        to: exit.targetMap,
        direction: exit.direction,
        targetSpawn: exit.targetSpawn,
      });
      
      setSelectedTarget(null);
      setSelectedType(null);
      return;
    }

    if (action === 'talk' && selectedTarget && selectedType === 'object') {
      const obj = selectedTarget as MapObject;
      if (obj.type === 'npc') {
        startDialogueSession(obj);
        return;
      }
    }

    onInteraction?.(action, selectedTarget as MapObject | MapExit);
  }, [currentMapId, selectedTarget, selectedType, onInteraction, startDialogueSession]);

  // Handle transition complete
  const handleTransitionComplete = useCallback(() => {
    if (transition) {
      setCurrentMapId(transition.to);
      
      // Set spawn for new map
      const spawn = getSpawnPoint(transition.to, transition.targetSpawn);
      if (spawn) {
        setSpawnPosition(gridToWorld(spawn.col, spawn.row));
        setSpawnFacing(spawn.facing as typeof spawnFacing);
      }
      
      setTransition(null);
    }
  }, [transition]);

  // Close panel
  const handleClosePanel = useCallback(() => {
    setSelectedTarget(null);
    setSelectedType(null);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (combatActive) {
          if (combat.state === CombatState.ENDED) {
            clearCombat();
          } else {
            clearCombatSelection();
          }
          return;
        }
        if (dialogueActive) {
          closeDialogue();
        } else if (selectedTarget) {
          handleClosePanel();
        } else {
          setPaused(p => !p);
          if (!paused) {
            playInteraction('cancel');
          } else {
            playInteraction('select');
          }
          onExit?.();
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    combatActive,
    combat.state,
    clearCombat,
    clearCombatSelection,
    dialogueActive,
    selectedTarget,
    handleClosePanel,
    closeDialogue,
    onExit,
    paused,
    playInteraction,
  ]);

  // Loading state
  if (!currentMap) {
    return (
      <div className="localmap-container">
        <div className="localmap-loading">
          <div className="loading-spinner" />
          <span>LOADING MAP...</span>
        </div>
      </div>
    );
  }

  const displayedDisposition = dialogueSession
    ? shiftDisposition(dialogueSession.npcDisposition, dialogueDispositionDelta)
    : 'neutral';

  return (
    <div className="localmap-container" ref={containerRef}>
      {/* Transition overlay */}
      {transition && (
        <MapTransition
          fromMap={transition.from}
          toMap={transition.to}
          direction={transition.direction}
          onComplete={handleTransitionComplete}
        />
      )}

      <div className="localmap-main">
        <div className="localmap-canvas-wrapper">
          <LocalMapCanvas
            map={currentMap}
            npcStates={combat.npcRenderStates || npcStates}
            initialPosition={spawnPosition || undefined}
            initialFacing={spawnFacing}
            onExitApproach={handleExitApproach}
            onObjectInteract={handleObjectInteract}
            onPositionChange={handlePositionChange}
            onIdleChange={setIdleSeconds}
            awarenessState={awarenessSnapshot.states}
            ambientShift={awarenessSnapshot.ambientShift}
            factionPressures={factionPressures}
            pressureZones={pressureZones}
            dormantThreads={dormantThreads}
            highlights={mapHighlight ? [mapHighlight] : []}
            paused={paused || !!transition || dialogueActive || combatActive}
            dimmed={dialogueActive || combatActive}
            onCanvasClick={combat.actions.handleMapClick}
            playerPositionOverride={combat.playerPositionOverride}
            playerFacingOverride={combat.playerFacingOverride}
            combatOverlay={combat.renderState}
          />
        </div>

        {/* HUD indicators */}
        <div className="localmap-hud">
          <div className="hud-time">
            <span className={`time-indicator time-${getTimeOfDay(clockState.time.hour)}`}>
              {formatTimeShort(clockState.time)}
            </span>
            <span className="time-day">Day {clockState.time.day + 1}</span>
            {clockState.paused && (
              <span className="time-paused">[PAUSED]</span>
            )}
          </div>
          <div className="hud-position">
            <span>({playerGridPos.col}, {playerGridPos.row})</span>
          </div>
        </div>

        <NotificationSystem
          notifications={consequenceNotifications}
          onDismiss={dismissNotification}
          onHighlight={handleNotificationHighlight}
        />

        {dialogueSession && (
          <DialogueOverlay
            active={dialogueActive}
            npcName={dialogueSession.npcName}
            npcFaction={dialogueSession.npcFaction}
            npcDisposition={displayedDisposition}
            response={dialogueResponse}
            socialEnergy={socialEnergy}
            loading={dialogueLoading}
            error={dialogueError}
            onSelectOption={handleDialogueOption}
            onExit={closeDialogue}
          />
        )}

        {combat.renderState && (
          <CombatOverlay
            active={combat.active}
            state={combat.state}
            round={combat.round}
            playerId={combat.renderState.playerId}
            combatants={combat.combatants}
            selectedAction={combat.selectedAction}
            selectedTargetId={combat.selectedTargetId}
            targetOptions={combat.targetOptions}
            intents={combat.intents}
            outcome={combat.outcome}
            onSelectAction={combat.actions.selectAction}
            onSelectTarget={combat.actions.selectTarget}
            onClearSelection={combat.actions.clearSelection}
            onClearCombat={combat.actions.clearCombat}
          />
        )}
      </div>

      <div className="localmap-sidebar">
        {!suppressPanels && (
          <InteractionPanel
            target={selectedTarget}
            type={selectedType}
            onAction={handleAction}
            onClose={handleClosePanel}
            playInteraction={playInteraction}
          />
        )}
      </div>

      {/* Pause overlay */}
      {paused && !transition && !dialogueActive && !combatActive && (
        <div className="localmap-pause-overlay">
          <div className="pause-menu">
            <h2>PAUSED</h2>
            <button onClick={() => { setPaused(false); playInteraction('select'); }}>Resume</button>
            <button onClick={onExit}>Exit to Menu</button>
          </div>
        </div>
      )}
    </div>
  );
}
