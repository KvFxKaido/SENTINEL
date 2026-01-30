import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LocalMapTemplate, Point, NPCObjectData } from './types';
import { TILE_SIZE, TILE_PROPERTIES } from './types';
import { AlertState } from './alertSystem';
import type { SimulatedNPC } from './usePatrolSimulation';
import {
  CombatActionType,
  CombatState,
  COMBAT_MAX_COMBATANTS,
  actionRequiresPosition,
  actionRequiresTarget,
  buildInjurySnapshot,
  computeFactionImpact,
  getActionRangeTiles,
  getCoverValueAtPosition,
  getDistanceTiles,
  getFacingFromDelta,
  getMovementRange,
  resolveCombatActionLocal,
  type CombatAction,
  type CombatActionResult,
  type CombatIntent,
  type CombatOutcome,
  type CombatRenderState,
  type CombatTargetInfo,
  type Combatant,
  type InjuryEffect,
} from './combat';
import { hasLineOfSight } from './collision';
import type { CombatEndResult } from '../../lib/gameApi';
import { endCombat } from '../../lib/gameApi';

const PLAYER_ID = 'player';

interface UseCombatOptions {
  map: LocalMapTemplate | null;
  npcStates: Map<string, SimulatedNPC>;
  playerPosition: Point;
  playerFacing: 'north' | 'south' | 'east' | 'west';
  paused: boolean;
  onCombatEnd?: (result: CombatEndResult) => void;
}

interface UseCombatReturn {
  active: boolean;
  state: CombatState;
  round: number;
  combatants: Combatant[];
  selectedAction: CombatActionType | null;
  selectedTargetId: string | null;
  targetOptions: CombatTargetInfo[];
  intents: CombatIntent[];
  outcome: CombatOutcome | null;
  renderState: CombatRenderState | null;
  playerPositionOverride?: Point;
  playerFacingOverride?: 'north' | 'south' | 'east' | 'west';
  npcRenderStates?: Map<string, SimulatedNPC>;
  actions: {
    selectAction: (action: CombatActionType) => void;
    selectTarget: (targetId: string) => void;
    clearSelection: () => void;
    handleMapClick: (position: Point) => void;
    clearCombat: () => void;
  };
}

export function useCombat({
  map,
  npcStates,
  playerPosition,
  playerFacing,
  paused,
  onCombatEnd,
}: UseCombatOptions): UseCombatReturn {
  const [combatState, setCombatState] = useState<CombatState>(CombatState.NONE);
  const [round, setRound] = useState(0);
  const [combatants, setCombatants] = useState<Combatant[]>([]);
  const [selectedAction, setSelectedAction] = useState<CombatActionType | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [intents, setIntents] = useState<CombatIntent[]>([]);
  const [outcome, setOutcome] = useState<CombatOutcome | null>(null);

  const combatantsRef = useRef<Combatant[]>([]);
  const roundRef = useRef(0);
  const combatCooldownRef = useRef(0);
  const injuryLedgerRef = useRef<Map<string, InjuryEffect[]>>(new Map());

  useEffect(() => {
    combatantsRef.current = combatants;
  }, [combatants]);

  useEffect(() => {
    roundRef.current = round;
  }, [round]);

  useEffect(() => {
    if (!map) return;
    setCombatState(CombatState.NONE);
    setRound(0);
    setCombatants([]);
    setSelectedAction(null);
    setSelectedTargetId(null);
    setIntents([]);
    setOutcome(null);
  }, [map?.id]);

  const finalizeCombat = useCallback((nextOutcome: CombatOutcome) => {
    combatCooldownRef.current = Date.now();
    setOutcome(nextOutcome);
    setCombatState(CombatState.ENDED);
    setSelectedAction(null);
    setSelectedTargetId(null);

    const injurySnapshot = buildInjurySnapshot(combatantsRef.current);
    Object.entries(injurySnapshot).forEach(([id, injuries]) => {
      injuryLedgerRef.current.set(id, injuries);
    });

    const endPayload: CombatEndResult = {
      ok: true,
      outcome: nextOutcome.outcome,
      faction_impact: nextOutcome.factionImpact,
      injuries: injurySnapshot,
      rounds: nextOutcome.rounds,
      meta: { mock: true },
    };
    onCombatEnd?.(endPayload);

    endCombat({
      outcome: nextOutcome.outcome,
      faction_impact: nextOutcome.factionImpact,
      injuries: injurySnapshot,
      rounds: nextOutcome.rounds,
    }).catch(() => {});
  }, [onCombatEnd]);

  const resolveAction = useCallback((action: CombatAction) => {
    if (!map) return;
    setCombatState(CombatState.RESOLVING);

    const { combatants: updated, result } = resolveCombatActionLocal(
      map,
      combatantsRef.current,
      action,
      roundRef.current
    );

    setCombatants(updated);
    const nextOutcome = evaluateOutcome(updated, result, roundRef.current);

    if (nextOutcome) {
      finalizeCombat(nextOutcome);
      return;
    }

    setSelectedAction(null);
    setSelectedTargetId(null);
    setCombatState(action.actorId === PLAYER_ID ? CombatState.NPC_TURN : CombatState.PLAYER_TURN);
  }, [map, finalizeCombat]);

  const executePlayerAction = useCallback((actionType: CombatActionType, targetId?: string, targetPosition?: Point) => {
    if (!map) return;
    const action: CombatAction = {
      type: actionType,
      actorId: PLAYER_ID,
      targetId,
      targetPosition,
    };
    resolveAction(action);
  }, [map, resolveAction]);

  const selectAction = useCallback((action: CombatActionType) => {
    if (combatState !== CombatState.PLAYER_TURN) return;
    if (action === CombatActionType.FLEE) {
      executePlayerAction(action);
      return;
    }
    setSelectedAction(action);
    if (selectedTargetId && actionRequiresTarget(action)) {
      executePlayerAction(action, selectedTargetId);
    }
  }, [combatState, executePlayerAction, selectedTargetId]);

  const selectTarget = useCallback((targetId: string) => {
    setSelectedTargetId(targetId);
    if (selectedAction && actionRequiresTarget(selectedAction) && combatState === CombatState.PLAYER_TURN) {
      executePlayerAction(selectedAction, targetId);
    }
  }, [selectedAction, combatState, executePlayerAction]);

  const clearSelection = useCallback(() => {
    setSelectedAction(null);
    setSelectedTargetId(null);
  }, []);

  const clearCombat = useCallback(() => {
    setCombatState(CombatState.NONE);
    setRound(0);
    setCombatants([]);
    setSelectedAction(null);
    setSelectedTargetId(null);
    setIntents([]);
    setOutcome(null);
  }, []);

  const handleMapClick = useCallback((position: Point) => {
    if (combatState !== CombatState.PLAYER_TURN) return;
    if (!selectedAction || !actionRequiresPosition(selectedAction)) return;
    executePlayerAction(selectedAction, undefined, position);
  }, [combatState, selectedAction, executePlayerAction]);

  const resolveNpcTurn = useCallback(() => {
    if (!map) return;
    let updated = combatantsRef.current;
    const currentRound = roundRef.current;
    const npcCombatants = updated.filter(combatant => !combatant.isPlayer && combatant.status === 'active');

    for (const npc of npcCombatants) {
      const intent = planNpcIntent(npc, updated, map);
      const npcAction: CombatAction = {
        type: intent.action,
        actorId: npc.id,
        targetId: intent.targetId,
        targetPosition: intent.targetPosition,
      };
      const resolved = resolveCombatActionLocal(map, updated, npcAction, currentRound);
      updated = resolved.combatants;
      const maybeOutcome = evaluateOutcome(updated, resolved.result, currentRound);
      if (maybeOutcome) {
        setCombatants(updated);
        finalizeCombat(maybeOutcome);
        return;
      }
    }

    setCombatants(updated);
    setRound(currentRound + 1);
    setCombatState(CombatState.PLAYER_TURN);
  }, [map, finalizeCombat]);

  useEffect(() => {
    if (combatState !== CombatState.NPC_TURN || paused) return;
    resolveNpcTurn();
  }, [combatState, paused, resolveNpcTurn]);

  useEffect(() => {
    if (!map || paused) return;
    if (combatState !== CombatState.NONE) return;

    const now = Date.now();
    if (now - combatCooldownRef.current < 2000) return;

    const engaged = Array.from(npcStates.values())
      .filter(npc => npc.alertState === AlertState.COMBAT)
      .sort((a, b) => getDistanceTiles(playerPosition, a.position) - getDistanceTiles(playerPosition, b.position))
      .slice(0, COMBAT_MAX_COMBATANTS - 1);

    if (engaged.length === 0) return;

    const combatantsInit: Combatant[] = [
      {
        id: PLAYER_ID,
        name: 'Player',
        isPlayer: true,
        position: playerPosition,
        facing: playerFacing,
        injuries: injuryLedgerRef.current.get(PLAYER_ID) || [],
        status: 'active',
      },
    ];

    engaged.forEach(npc => {
      const mapNpc = map.objects.find(obj => obj.id === npc.id);
      const npcName = mapNpc?.name || npc.id;
      const npcData = npc.data as NPCObjectData;
      combatantsInit.push({
        id: npc.id,
        name: npcName,
        isPlayer: false,
        faction: npcData?.faction ?? null,
        position: npc.position,
        facing: npc.facing,
        injuries: injuryLedgerRef.current.get(npc.id) || [],
        status: 'active',
        data: npcData,
      });
    });

    setCombatants(combatantsInit);
    setRound(1);
    setCombatState(CombatState.PLAYER_TURN);
    setOutcome(null);
    setSelectedAction(null);
    setSelectedTargetId(getNearestEnemyId(combatantsInit, playerPosition));
  }, [combatState, map, npcStates, paused, playerFacing, playerPosition]);

  useEffect(() => {
    if (combatState !== CombatState.PLAYER_TURN || !map) return;
    const player = combatantsRef.current.find(combatant => combatant.isPlayer);
    if (!player) return;
    const nextIntents = combatantsRef.current
      .filter(combatant => !combatant.isPlayer && combatant.status === 'active')
      .map(npc => planNpcIntent(npc, combatantsRef.current, map));
    setIntents(nextIntents);
  }, [combatState, map, combatants]);

  const targetOptions = useMemo(() => {
    if (!map || !selectedAction || !actionRequiresTarget(selectedAction)) return [];
    const player = combatants.find(combatant => combatant.id === PLAYER_ID);
    if (!player) return [];
    const range = getActionRangeTiles(selectedAction);

    return combatants
      .filter(combatant => !combatant.isPlayer && combatant.status === 'active')
      .map(combatant => {
        const distance = getDistanceTiles(player.position, combatant.position);
        const coverValue = getCoverValueAtPosition(map, combatant.position);
        return {
          id: combatant.id,
          name: combatant.name,
          faction: combatant.faction,
          distance,
          coverValue,
          inRange: distance <= range,
        };
      });
  }, [combatants, map, selectedAction]);

  const playerCombatant = combatants.find(combatant => combatant.id === PLAYER_ID);
  const playerPositionOverride = combatState !== CombatState.NONE ? playerCombatant?.position : undefined;
  const playerFacingOverride = combatState !== CombatState.NONE ? playerCombatant?.facing : undefined;

  const npcRenderStates = useMemo(() => {
    if (combatState === CombatState.NONE) return undefined;
    const merged = new Map(npcStates);
    combatants
      .filter(combatant => !combatant.isPlayer)
      .forEach(combatant => {
        const existing = npcStates.get(combatant.id);
        const data = (combatant.data as NPCObjectData | undefined) ?? existing?.data ?? {
          npcId: combatant.id,
          faction: combatant.faction ?? null,
          disposition: 'hostile',
        };
        merged.set(combatant.id, {
          id: combatant.id,
          position: combatant.position,
          facing: combatant.facing,
          alertState: AlertState.COMBAT,
          alertLevel: 100,
          data,
        });
      });
    return merged;
  }, [combatState, combatants, npcStates]);

  const renderState = useMemo<CombatRenderState | null>(() => {
    if (combatState === CombatState.NONE) return null;
    const activeCombatantId = combatState === CombatState.PLAYER_TURN
      ? PLAYER_ID
      : combatants.find(combatant => !combatant.isPlayer && combatant.status === 'active')?.id;
    const activeCombatant = combatants.find(combatant => combatant.id === activeCombatantId);
    return {
      active: true,
      state: combatState,
      round,
      activeCombatantId,
      combatants,
      selectedAction,
      selectedTargetId,
      movementRange: activeCombatant ? getMovementRange(activeCombatant) : 0,
      intents,
      playerId: PLAYER_ID,
    };
  }, [combatState, round, combatants, selectedAction, selectedTargetId, intents]);

  return {
    active: combatState !== CombatState.NONE,
    state: combatState,
    round,
    combatants,
    selectedAction,
    selectedTargetId,
    targetOptions,
    intents,
    outcome,
    renderState,
    playerPositionOverride,
    playerFacingOverride,
    npcRenderStates,
    actions: {
      selectAction,
      selectTarget,
      clearSelection,
      handleMapClick,
      clearCombat,
    },
  };
}

// ============================================================================
// Planning
// ============================================================================

function planNpcIntent(
  npc: Combatant,
  combatants: Combatant[],
  map: LocalMapTemplate
): CombatIntent {
  const player = combatants.find(combatant => combatant.isPlayer);
  if (!player) {
    return { npcId: npc.id, action: CombatActionType.MOVE };
  }

  if (npc.injuries.length > 0) {
    return { npcId: npc.id, action: CombatActionType.FLEE, rationale: 'injured' };
  }

  const canSee = hasLineOfSight(map, npc.position, player.position);
  const distance = getDistanceTiles(npc.position, player.position);

  if (canSee && distance <= getActionRangeTiles(CombatActionType.FIRE)) {
    const action = distance <= 1.2 ? CombatActionType.STRIKE : CombatActionType.FIRE;
    return { npcId: npc.id, action, targetId: player.id, rationale: 'line_of_sight' };
  }

  const coverTarget = findNearestCover(map, npc.position, player.position);
  if (coverTarget) {
    return {
      npcId: npc.id,
      action: CombatActionType.MOVE,
      targetPosition: coverTarget,
      rationale: 'seek_cover',
    };
  }

  const dx = player.position.x - npc.position.x;
  const dy = player.position.y - npc.position.y;
  const facing = getFacingFromDelta(dx, dy);
  return {
    npcId: npc.id,
    action: CombatActionType.MOVE,
    targetPosition: {
      x: npc.position.x + (dx / Math.max(1, Math.abs(dx) + Math.abs(dy))) * TILE_SIZE,
      y: npc.position.y + (dy / Math.max(1, Math.abs(dx) + Math.abs(dy))) * TILE_SIZE,
    },
    rationale: `close_distance_${facing}`,
  };
}

function findNearestCover(map: LocalMapTemplate, from: Point, playerPos: Point): Point | null {
  let best: Point | null = null;
  let bestScore = Number.POSITIVE_INFINITY;
  const searchTiles = 6;

  for (let row = 0; row < map.height; row++) {
    for (let col = 0; col < map.width; col++) {
      const tile = map.tiles[row][col];
      if (tile === undefined || tile === null) continue;
      const coverValue = TILE_PROPERTIES[tile].coverValue;
      if (coverValue === 0) continue;

      const x = col * TILE_SIZE + TILE_SIZE / 2;
      const y = row * TILE_SIZE + TILE_SIZE / 2;
      const point = { x, y };
      const distanceToNpc = getDistanceTiles(from, point);
      if (distanceToNpc > searchTiles) continue;

      const distanceToPlayer = getDistanceTiles(playerPos, point);
      const score = distanceToNpc - distanceToPlayer * 0.2;
      if (score < bestScore) {
        bestScore = score;
        best = point;
      }
    }
  }

  return best;
}

function evaluateOutcome(
  combatants: Combatant[],
  result: CombatActionResult,
  round: number
): CombatOutcome | null {
  const player = combatants.find(combatant => combatant.isPlayer);
  const activeNpcs = combatants.filter(combatant => !combatant.isPlayer && combatant.status === 'active');
  const fledNpcs = combatants.filter(combatant => !combatant.isPlayer && combatant.status === 'fled');

  if (result.outcome === 'talk_success') {
    const impact = computeFactionImpact(combatants, 'talk_success');
    return {
      outcome: 'talk_success',
      factionImpact: impact,
      injuries: buildInjurySnapshot(combatants),
      rounds: round,
    };
  }

  if (player?.status === 'fled') {
    const impact = computeFactionImpact(combatants, 'player_fled');
    return {
      outcome: 'player_fled',
      factionImpact: impact,
      injuries: buildInjurySnapshot(combatants),
      rounds: round,
    };
  }

  if (player?.status === 'down') {
    const impact = computeFactionImpact(combatants, 'player_down');
    return {
      outcome: 'player_down',
      factionImpact: impact,
      injuries: buildInjurySnapshot(combatants),
      rounds: round,
    };
  }

  if (activeNpcs.length === 0) {
    const outcome = fledNpcs.length > 0 ? 'npc_fled' : 'npc_down';
    const impact = computeFactionImpact(combatants, outcome);
    return {
      outcome,
      factionImpact: impact,
      injuries: buildInjurySnapshot(combatants),
      rounds: round,
    };
  }

  return null;
}

function getNearestEnemyId(combatants: Combatant[], playerPos: Point): string | null {
  const enemies = combatants.filter(combatant => !combatant.isPlayer);
  if (enemies.length === 0) return null;
  let best = enemies[0];
  let bestDist = getDistanceTiles(playerPos, best.position);
  enemies.slice(1).forEach(enemy => {
    const dist = getDistanceTiles(playerPos, enemy.position);
    if (dist < bestDist) {
      best = enemy;
      bestDist = dist;
    }
  });
  return best.id;
}
