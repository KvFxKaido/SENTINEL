/**
 * Combat system (Phase 5)
 *
 * Room-scale tactical combat overlay with injuries (not HP).
 * Alternating initiative: player turn, NPC turn.
 */

import type { LocalMapTemplate, Point } from './types';
import { TILE_SIZE, TILE_PROPERTIES } from './types';
import {
  clampToMapBounds,
  checkCollision,
  euclideanDistance,
  getTileAt,
  hasLineOfSight,
  worldToGrid,
} from './collision';

// ============================================================================
// Constants
// ============================================================================

export const COMBAT_MAX_COMBATANTS = 6;
export const COMBAT_MOVE_RANGE_TILES = 3;
export const COMBAT_FIRE_RANGE_TILES = 8;
export const COMBAT_SUPPRESS_RANGE_TILES = 6;
export const COMBAT_STRIKE_RANGE_TILES = 1.6;

export const COMBAT_MOVE_RANGE = COMBAT_MOVE_RANGE_TILES * TILE_SIZE;

// ============================================================================
// Types
// ============================================================================

export enum CombatState {
  NONE = 'none',
  INITIATING = 'initiating',
  PLAYER_TURN = 'player_turn',
  NPC_TURN = 'npc_turn',
  RESOLVING = 'resolving',
  ENDED = 'ended',
}

export enum CombatActionType {
  MOVE = 'move',
  FIRE = 'fire',
  STRIKE = 'strike',
  SUPPRESS = 'suppress',
  INTERACT = 'interact',
  TALK = 'talk',
  FLEE = 'flee',
}

export const ACTION_ORDER: CombatActionType[] = [
  CombatActionType.MOVE,
  CombatActionType.FIRE,
  CombatActionType.STRIKE,
  CombatActionType.SUPPRESS,
  CombatActionType.INTERACT,
  CombatActionType.TALK,
  CombatActionType.FLEE,
];

export const ACTION_LABELS: Record<CombatActionType, string> = {
  [CombatActionType.MOVE]: 'Move',
  [CombatActionType.FIRE]: 'Fire',
  [CombatActionType.STRIKE]: 'Strike',
  [CombatActionType.SUPPRESS]: 'Suppress',
  [CombatActionType.INTERACT]: 'Interact',
  [CombatActionType.TALK]: 'Talk',
  [CombatActionType.FLEE]: 'Flee',
};

export enum InjuryType {
  IMPAIRED_MOVEMENT = 'impaired_movement',
  REDUCED_ACCURACY = 'reduced_accuracy',
  GEAR_DAMAGE = 'gear_damage',
  SCARRED = 'scarred',
}

export interface InjuryEffect {
  type: InjuryType;
  severity: number;
  description: string;
  accuracyPenalty?: number;
  movementPenalty?: number;
}

export interface CombatTemporaryEffects {
  suppressedUntilRound?: number;
  defenseBonus?: number;
  defenseUntilRound?: number;
}

export interface Combatant {
  id: string;
  name: string;
  isPlayer: boolean;
  faction?: string | null;
  position: Point;
  facing: 'north' | 'south' | 'east' | 'west';
  injuries: InjuryEffect[];
  status: 'active' | 'fled' | 'down';
  data?: unknown;
  temporaryEffects?: CombatTemporaryEffects;
  intent?: CombatActionType;
}

export interface CombatIntent {
  npcId: string;
  action: CombatActionType;
  targetId?: string;
  targetPosition?: Point;
  rationale?: string;
}

export interface CombatAction {
  type: CombatActionType;
  actorId: string;
  targetId?: string;
  targetPosition?: Point;
}

export interface CombatActionResult {
  action: CombatAction;
  hit?: boolean;
  movedTo?: Point;
  injuryApplied?: InjuryEffect;
  suppressed?: boolean;
  outcome?: 'talk_success' | 'talk_failed' | 'fled';
  targetId?: string;
}

export interface CombatOutcome {
  outcome: 'player_fled' | 'npc_fled' | 'player_down' | 'npc_down' | 'talk_success';
  factionImpact: Record<string, number>;
  injuries: Record<string, InjuryEffect[]>;
  rounds: number;
}

export interface CombatTargetInfo {
  id: string;
  name: string;
  faction?: string | null;
  distance: number;
  coverValue: number;
  inRange: boolean;
}

export interface CombatRenderState {
  active: boolean;
  state: CombatState;
  round: number;
  activeCombatantId?: string;
  combatants: Combatant[];
  selectedAction?: CombatActionType | null;
  selectedTargetId?: string | null;
  movementRange: number;
  intents: CombatIntent[];
  playerId: string;
}

// ============================================================================
// Injury Library
// ============================================================================

const INJURY_TEMPLATES: Record<InjuryType, Omit<InjuryEffect, 'severity'>> = {
  [InjuryType.IMPAIRED_MOVEMENT]: {
    type: InjuryType.IMPAIRED_MOVEMENT,
    description: 'Impaired movement',
    movementPenalty: 0.2,
  },
  [InjuryType.REDUCED_ACCURACY]: {
    type: InjuryType.REDUCED_ACCURACY,
    description: 'Reduced accuracy',
    accuracyPenalty: 0.15,
  },
  [InjuryType.GEAR_DAMAGE]: {
    type: InjuryType.GEAR_DAMAGE,
    description: 'Gear damage',
    accuracyPenalty: 0.1,
  },
  [InjuryType.SCARRED]: {
    type: InjuryType.SCARRED,
    description: 'Visible scars',
  },
};

export function createInjury(type: InjuryType, severity: number = 1): InjuryEffect {
  const template = INJURY_TEMPLATES[type];
  return {
    type,
    severity,
    description: template.description,
    accuracyPenalty: template.accuracyPenalty ? template.accuracyPenalty * severity : undefined,
    movementPenalty: template.movementPenalty ? template.movementPenalty * severity : undefined,
  };
}

// ============================================================================
// Helpers
// ============================================================================

export function actionRequiresTarget(action: CombatActionType): boolean {
  return (
    action === CombatActionType.FIRE ||
    action === CombatActionType.STRIKE ||
    action === CombatActionType.SUPPRESS ||
    action === CombatActionType.TALK
  );
}

export function actionRequiresPosition(action: CombatActionType): boolean {
  return action === CombatActionType.MOVE || action === CombatActionType.INTERACT;
}

export function getActionRangeTiles(action: CombatActionType): number {
  switch (action) {
    case CombatActionType.STRIKE:
      return COMBAT_STRIKE_RANGE_TILES;
    case CombatActionType.SUPPRESS:
      return COMBAT_SUPPRESS_RANGE_TILES;
    case CombatActionType.FIRE:
      return COMBAT_FIRE_RANGE_TILES;
    default:
      return COMBAT_FIRE_RANGE_TILES;
  }
}

export function getDistanceTiles(from: Point, to: Point): number {
  return euclideanDistance(from, to) / TILE_SIZE;
}

export function getCoverValueAtPosition(map: LocalMapTemplate, position: Point): number {
  const grid = worldToGrid(position.x, position.y);
  const tile = getTileAt(map, grid.col, grid.row);
  if (tile === null) return 0;
  return TILE_PROPERTIES[tile].coverValue;
}

export function getCoverLabel(coverValue: number): string {
  if (coverValue >= 2) return 'Full';
  if (coverValue === 1) return 'Half';
  return 'None';
}

export function getAccuracyPenalty(injuries: InjuryEffect[]): number {
  return injuries.reduce((sum, injury) => sum + (injury.accuracyPenalty || 0), 0);
}

export function getMovementPenalty(injuries: InjuryEffect[]): number {
  return injuries.reduce((sum, injury) => sum + (injury.movementPenalty || 0), 0);
}

export function getMovementRange(combatant: Combatant): number {
  const penalty = Math.min(0.6, getMovementPenalty(combatant.injuries));
  const range = COMBAT_MOVE_RANGE * (1 - penalty);
  return Math.max(TILE_SIZE * 1.5, range);
}

export function calculateHitChance(params: {
  map: LocalMapTemplate;
  attacker: Combatant;
  target: Combatant;
  actionType: CombatActionType;
  round: number;
}): number {
  const { map, attacker, target, actionType, round } = params;
  const distanceTiles = getDistanceTiles(attacker.position, target.position);
  const coverValue = getCoverValueAtPosition(map, target.position);
  const coverPenalty = coverValue >= 2 ? 0.3 : coverValue === 1 ? 0.15 : 0;

  const base =
    actionType === CombatActionType.STRIKE ? 0.75 :
    actionType === CombatActionType.SUPPRESS ? 0.5 :
    0.6;

  const distancePenalty =
    actionType === CombatActionType.STRIKE
      ? Math.max(0, distanceTiles - 1) * 0.2
      : Math.max(0, distanceTiles - 3) * 0.05;

  const injuryPenalty = getAccuracyPenalty(attacker.injuries);

  const suppressedPenalty =
    attacker.temporaryEffects?.suppressedUntilRound && attacker.temporaryEffects.suppressedUntilRound >= round
      ? 0.2
      : 0;

  const defenseBonus =
    target.temporaryEffects?.defenseUntilRound && target.temporaryEffects.defenseUntilRound >= round
      ? target.temporaryEffects.defenseBonus || 0
      : 0;

  const chance = base - distancePenalty - coverPenalty - injuryPenalty - suppressedPenalty - defenseBonus;
  return Math.max(0.1, Math.min(0.9, chance));
}

export function getFacingFromDelta(dx: number, dy: number): 'north' | 'south' | 'east' | 'west' {
  if (Math.abs(dx) > Math.abs(dy)) {
    return dx >= 0 ? 'east' : 'west';
  }
  return dy >= 0 ? 'south' : 'north';
}

export function applyInjury(target: Combatant, injury: InjuryEffect): Combatant {
  const existingIndex = target.injuries.findIndex(existing => existing.type === injury.type);
  const injuries = [...target.injuries];
  if (existingIndex >= 0) {
    const existing = injuries[existingIndex];
    const nextSeverity = Math.min(2, existing.severity + 1);
    injuries[existingIndex] = createInjury(existing.type, nextSeverity);
  } else {
    injuries.push(injury);
  }
  return { ...target, injuries };
}

export function isCombatantDown(combatant: Combatant): boolean {
  const maxInjuries = combatant.isPlayer ? 3 : 2;
  return combatant.injuries.length >= maxInjuries;
}

export function resolveCombatActionLocal(
  map: LocalMapTemplate,
  combatants: Combatant[],
  action: CombatAction,
  round: number
): { combatants: Combatant[]; result: CombatActionResult } {
  const byId = new Map<string, Combatant>();
  combatants.forEach(combatant => {
    byId.set(combatant.id, { ...combatant });
  });

  const actor = byId.get(action.actorId);
  if (!actor || actor.status !== 'active') {
    return { combatants, result: { action } };
  }

  const result: CombatActionResult = { action, targetId: action.targetId };

  switch (action.type) {
    case CombatActionType.MOVE:
    case CombatActionType.INTERACT: {
      if (!action.targetPosition) break;
      const range = getMovementRange(actor);
      const dx = action.targetPosition.x - actor.position.x;
      const dy = action.targetPosition.y - actor.position.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;
      const clampedDistance = Math.min(range, distance);
      const desired = {
        x: actor.position.x + (dx / distance) * clampedDistance,
        y: actor.position.y + (dy / distance) * clampedDistance,
      };
      const clamped = clampToMapBounds(map, desired, TILE_SIZE / 3);
      const collision = checkCollision(map, actor.position, clamped, TILE_SIZE / 3);
      const newFacing = getFacingFromDelta(dx, dy);
      const moved = { ...actor, position: collision.newPosition, facing: newFacing };

      if (action.type === CombatActionType.INTERACT) {
        const coverValue = getCoverValueAtPosition(map, moved.position);
        if (coverValue > 0) {
          moved.temporaryEffects = {
            ...(moved.temporaryEffects || {}),
            defenseBonus: coverValue >= 2 ? 0.2 : 0.1,
            defenseUntilRound: round + 1,
          };
        }
      }

      byId.set(actor.id, moved);
      result.movedTo = collision.newPosition;
      break;
    }
    case CombatActionType.FLEE: {
      byId.set(actor.id, { ...actor, status: 'fled' });
      result.outcome = 'fled';
      break;
    }
    case CombatActionType.TALK: {
      const baseChance = 0.25;
      const target = action.targetId ? byId.get(action.targetId) : undefined;
      const targetInjured = target ? target.injuries.length > 0 : false;
      const attackerInjured = actor.injuries.length > 0;
      const chance = Math.max(
        0.05,
        Math.min(0.6, baseChance + (targetInjured ? 0.15 : 0) - (attackerInjured ? 0.1 : 0))
      );
      result.outcome = Math.random() < chance ? 'talk_success' : 'talk_failed';
      break;
    }
    case CombatActionType.SUPPRESS:
    case CombatActionType.FIRE:
    case CombatActionType.STRIKE: {
      if (!action.targetId) break;
      const target = byId.get(action.targetId);
      if (!target || target.status !== 'active') break;

      if (action.type !== CombatActionType.STRIKE && !hasLineOfSight(map, actor.position, target.position)) {
        result.hit = false;
        break;
      }

      if (action.type === CombatActionType.SUPPRESS) {
        const suppressedTarget = {
          ...target,
          temporaryEffects: {
            ...(target.temporaryEffects || {}),
            suppressedUntilRound: round + 1,
          },
        };
        byId.set(target.id, suppressedTarget);
        result.suppressed = true;
        result.hit = true;
        break;
      }

      const hitChance = calculateHitChance({
        map,
        attacker: actor,
        target,
        actionType: action.type,
        round,
      });
      const hit = Math.random() < hitChance;
      result.hit = hit;

      if (hit) {
        const injuryType = pickInjuryType(action.type);
        const injured = applyInjury(target, createInjury(injuryType));
        const downed = isCombatantDown(injured);
        byId.set(target.id, { ...injured, status: downed ? 'down' : injured.status });
        result.injuryApplied = createInjury(injuryType);
      }
      break;
    }
    default:
      break;
  }

  const updated = combatants.map(combatant => byId.get(combatant.id) || combatant);
  return { combatants: updated, result };
}

export function buildInjurySnapshot(combatants: Combatant[]): Record<string, InjuryEffect[]> {
  const snapshot: Record<string, InjuryEffect[]> = {};
  combatants.forEach(combatant => {
    if (combatant.injuries.length > 0) {
      snapshot[combatant.id] = combatant.injuries;
    }
  });
  return snapshot;
}

export function computeFactionImpact(
  combatants: Combatant[],
  outcome: CombatOutcome['outcome']
): Record<string, number> {
  const impact: Record<string, number> = {};
  const npcFactions = new Set(
    combatants
      .filter(combatant => !combatant.isPlayer)
      .map(combatant => combatant.faction)
      .filter((faction): faction is string => !!faction)
  );

  const delta =
    outcome === 'talk_success' ? 1 :
    outcome === 'npc_down' ? -2 :
    outcome === 'npc_fled' ? -1 :
    outcome === 'player_down' ? -2 :
    outcome === 'player_fled' ? -1 :
    0;

  npcFactions.forEach(faction => {
    impact[faction] = (impact[faction] || 0) + delta;
  });
  return impact;
}

// ============================================================================
// Internal
// ============================================================================

function pickInjuryType(actionType: CombatActionType): InjuryType {
  const roll = Math.random();
  if (actionType === CombatActionType.STRIKE) {
    if (roll < 0.5) return InjuryType.IMPAIRED_MOVEMENT;
    if (roll < 0.8) return InjuryType.REDUCED_ACCURACY;
    return InjuryType.SCARRED;
  }
  if (roll < 0.4) return InjuryType.GEAR_DAMAGE;
  if (roll < 0.8) return InjuryType.REDUCED_ACCURACY;
  return InjuryType.SCARRED;
}
