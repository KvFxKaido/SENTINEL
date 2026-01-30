import type { LocalMapTemplate, Point, MapObject, NPCObjectData } from './types';
import { NPC_DETECTION_RANGE } from './types';
import { hasLineOfSight, euclideanDistance } from './collision';

// ============================================================================
// Types
// ============================================================================

export enum AlertState {
  PATROLLING = 'patrolling',
  INVESTIGATING = 'investigating',
  COMBAT = 'combat',
}

export interface NPCAlertData {
  state: AlertState;
  targetPosition: Point | null; // Where they are investigating/fighting
  lastSeenPosition: Point | null; // Last known player position
  alertLevel: number; // 0-100, transitions states
  investigationTimer: number; // ms remaining in investigation
}

// ============================================================================
// Constants
// ============================================================================

const ALERT_DECAY_RATE = 20; // Per second
const ALERT_BUILD_RATE = 60; // Per second (when visible)
const INVESTIGATION_DURATION = 5000; // ms
const DETECTION_CONE_ANGLE = Math.PI / 2; // 90 degrees

// ============================================================================
// Alert Manager
// ============================================================================

export class AlertManager {
  private npcStates: Map<string, NPCAlertData> = new Map();

  constructor() {}

  getAlertState(npcId: string): NPCAlertData {
    if (!this.npcStates.has(npcId)) {
      this.npcStates.set(npcId, {
        state: AlertState.PATROLLING,
        targetPosition: null,
        lastSeenPosition: null,
        alertLevel: 0,
        investigationTimer: 0,
      });
    }
    return this.npcStates.get(npcId)!;
  }

  update(
    npcId: string,
    npcPos: Point,
    npcFacing: string,
    playerPos: Point,
    map: LocalMapTemplate,
    deltaMs: number,
    timeOfDay: string
  ) {
    const state = this.getAlertState(npcId);
    const dist = euclideanDistance(npcPos, playerPos);
    
    // Calculate detection range based on time of day
    let detectionRange = NPC_DETECTION_RANGE;
    if (timeOfDay === 'night' || timeOfDay === 'evening') {
      detectionRange *= 0.7; // Reduced visibility
    }

    // Check visibility
    let isVisible = false;
    if (dist < detectionRange) {
      if (hasLineOfSight(map, npcPos, playerPos)) {
        // Check facing cone
        const angleToPlayer = Math.atan2(playerPos.y - npcPos.y, playerPos.x - npcPos.x);
        const facingAngle = this.getFacingAngle(npcFacing);
        
        let angleDiff = Math.abs(angleToPlayer - facingAngle);
        // Normalize angle difference to 0-PI
        if (angleDiff > Math.PI) angleDiff = 2 * Math.PI - angleDiff;

        if (angleDiff < DETECTION_CONE_ANGLE / 2) {
          isVisible = true;
        }
      }
    }

    // Update Alert Level
    if (isVisible) {
      state.alertLevel = Math.min(100, state.alertLevel + (ALERT_BUILD_RATE * deltaMs) / 1000);
      state.lastSeenPosition = { ...playerPos };
    } else {
      state.alertLevel = Math.max(0, state.alertLevel - (ALERT_DECAY_RATE * deltaMs) / 1000);
    }

    // State Transitions
    switch (state.state) {
      case AlertState.PATROLLING:
        if (state.alertLevel >= 50) {
          state.state = AlertState.INVESTIGATING;
          state.targetPosition = state.lastSeenPosition || playerPos;
          state.investigationTimer = INVESTIGATION_DURATION;
        }
        break;

      case AlertState.INVESTIGATING:
        if (state.alertLevel >= 90) {
          state.state = AlertState.COMBAT;
        } else if (state.alertLevel <= 0 && state.investigationTimer <= 0) {
          state.state = AlertState.PATROLLING;
          state.targetPosition = null;
        } else if (!isVisible) {
          state.investigationTimer -= deltaMs;
        }
        break;

      case AlertState.COMBAT:
        if (state.alertLevel <= 0) {
          // Lost them
          state.state = AlertState.INVESTIGATING;
          state.investigationTimer = INVESTIGATION_DURATION;
        }
        break;
    }
  }

  private getFacingAngle(facing: string): number {
    switch (facing) {
      case 'north': return -Math.PI / 2;
      case 'south': return Math.PI / 2;
      case 'east': return 0;
      case 'west': return Math.PI;
      default: return 0;
    }
  }
}
