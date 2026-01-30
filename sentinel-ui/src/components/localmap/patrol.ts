import type { LocalMapTemplate, Point, GridPosition, NPCObjectData } from './types';
import { MOVEMENT_SPEED, TILE_SIZE } from './types';
import { 
  gridToWorld, 
  worldToGrid, 
  checkCollision, 
  euclideanDistance 
} from './collision';
import { AlertManager, AlertState } from './alertSystem';

// ============================================================================
// Types
// ============================================================================

export interface NPCSimulationState {
  id: string;
  position: Point;
  facing: 'north' | 'south' | 'east' | 'west';
  velocity: Point;
  currentPathIndex: number;
  waitTime: number; // ms to wait at current node
  data: NPCObjectData;
}

export interface PatrolContext {
  map: LocalMapTemplate;
  deltaMs: number;
  alertManager: AlertManager;
  playerPos: Point;
  timeOfDay: string;
}

interface PatrolBehavior {
  update(npc: NPCSimulationState, context: PatrolContext): void;
}

// ============================================================================
// Behaviors
// ============================================================================

class SimplePatrol implements PatrolBehavior {
  update(npc: NPCSimulationState, context: PatrolContext) {
    const { map, deltaMs, alertManager } = context;
    const alertData = alertManager.getAlertState(npc.id);

    // Stop if in combat (phase 5 will handle combat movement)
    if (alertData.state === AlertState.COMBAT) {
      return; 
    }

    // Investigating logic
    if (alertData.state === AlertState.INVESTIGATING && alertData.targetPosition) {
      this.moveTo(npc, alertData.targetPosition, deltaMs, map, true);
      return;
    }

    // Patrolling logic
    if (!npc.data.patrolRoute || npc.data.patrolRoute.length === 0) {
      return; // No patrol route, stay put
    }

    if (npc.waitTime > 0) {
      npc.waitTime -= deltaMs;
      return;
    }

    const targetGrid = npc.data.patrolRoute[npc.currentPathIndex];
    const targetPos = gridToWorld(targetGrid.col, targetGrid.row);

    if (this.hasReached(npc.position, targetPos)) {
      npc.waitTime = 1000; // Wait 1s at each node
      npc.currentPathIndex = (npc.currentPathIndex + 1) % npc.data.patrolRoute.length;
    } else {
      this.moveTo(npc, targetPos, deltaMs, map);
    }
  }

  protected moveTo(npc: NPCSimulationState, target: Point, deltaMs: number, map: LocalMapTemplate, run: boolean = false) {
    const dx = target.x - npc.position.x;
    const dy = target.y - npc.position.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist < 1) return;

    let speed = MOVEMENT_SPEED * (deltaMs / 16.66); // Normalize to 60fps
    if (run) speed *= 1.5;

    const moveX = (dx / dist) * speed;
    const moveY = (dy / dist) * speed;

    // Update facing
    if (Math.abs(moveX) > Math.abs(moveY)) {
      npc.facing = moveX > 0 ? 'east' : 'west';
    } else {
      npc.facing = moveY > 0 ? 'south' : 'north';
    }

    // Collision check
    const newPos = { x: npc.position.x + moveX, y: npc.position.y + moveY };
    const collision = checkCollision(map, npc.position, newPos, 10); // 10 radius for NPC
    
    npc.position = collision.newPosition;
  }

  protected hasReached(current: Point, target: Point): boolean {
    return euclideanDistance(current, target) < 4;
  }
}

class SweepPatrol extends SimplePatrol {
  // Lattice: Coordinated, predictable.
  // Overrides wait time to be shorter for continuous sweeping look.
  update(npc: NPCSimulationState, context: PatrolContext) {
    const { map, deltaMs, alertManager } = context;
    const alertData = alertManager.getAlertState(npc.id);

    if (alertData.state !== AlertState.PATROLLING) {
      super.update(npc, context);
      return;
    }

    // Standard patrol but strict
    if (!npc.data.patrolRoute || npc.data.patrolRoute.length === 0) return;

    if (npc.waitTime > 0) {
      npc.waitTime -= deltaMs;
      // Scan around while waiting? (Visual only for now)
      return;
    }

    const targetGrid = npc.data.patrolRoute[npc.currentPathIndex];
    const targetPos = gridToWorld(targetGrid.col, targetGrid.row);

    if (this.hasReached(npc.position, targetPos)) {
      npc.waitTime = 2000; // Longer stops for "inspection"
      npc.currentPathIndex = (npc.currentPathIndex + 1) % npc.data.patrolRoute.length;
    } else {
      this.moveTo(npc, targetPos, deltaMs, map);
    }
  }
}

class WanderPatrol extends SimplePatrol {
  // Ember: Loose, wandering.
  // Uses patrol route nodes as anchors but wanders near them.
  
  private currentRandomTarget: Point | null = null;

  update(npc: NPCSimulationState, context: PatrolContext) {
    const { map, deltaMs, alertManager } = context;
    const alertData = alertManager.getAlertState(npc.id);

    if (alertData.state !== AlertState.PATROLLING) {
      super.update(npc, context);
      return;
    }

    if (!npc.data.patrolRoute || npc.data.patrolRoute.length === 0) return;

    if (npc.waitTime > 0) {
      npc.waitTime -= deltaMs;
      return;
    }

    // Pick a new random target near the current patrol node if needed
    if (!this.currentRandomTarget) {
      const anchorGrid = npc.data.patrolRoute[npc.currentPathIndex];
      const anchorPos = gridToWorld(anchorGrid.col, anchorGrid.row);
      
      // Random offset within 3 tiles
      const offsetX = (Math.random() - 0.5) * TILE_SIZE * 6;
      const offsetY = (Math.random() - 0.5) * TILE_SIZE * 6;
      
      this.currentRandomTarget = {
        x: anchorPos.x + offsetX,
        y: anchorPos.y + offsetY
      };
    }

    if (this.hasReached(npc.position, this.currentRandomTarget)) {
      npc.waitTime = 500 + Math.random() * 2000; // Random wait
      npc.currentPathIndex = (npc.currentPathIndex + 1) % npc.data.patrolRoute.length;
      this.currentRandomTarget = null;
    } else {
      // Slower movement for wandering
      this.moveTo(npc, this.currentRandomTarget, deltaMs * 0.7, map);
    }
  }
}

class StaticWatch implements PatrolBehavior {
  // Ghost: Teleports.
  update(npc: NPCSimulationState, context: PatrolContext) {
    const { deltaMs, alertManager } = context;
    const alertData = alertManager.getAlertState(npc.id);

    // If investigating, they move normally (or fast)
    if (alertData.state !== AlertState.PATROLLING) {
       // Fallback to simple movement for investigation
       new SimplePatrol().update(npc, context);
       return;
    }

    if (!npc.data.patrolRoute || npc.data.patrolRoute.length === 0) return;

    if (npc.waitTime > 0) {
      npc.waitTime -= deltaMs;
      return;
    }

    // Instant teleport to next node
    npc.currentPathIndex = (npc.currentPathIndex + 1) % npc.data.patrolRoute.length;
    const targetGrid = npc.data.patrolRoute[npc.currentPathIndex];
    const targetPos = gridToWorld(targetGrid.col, targetGrid.row);
    
    npc.position = targetPos;
    npc.waitTime = 5000; // Stay for 5s
  }
}

class RitualCircuit extends SimplePatrol {
  // Covenant: Precise loops.
  update(npc: NPCSimulationState, context: PatrolContext) {
    // For now, same as simple patrol but very rigid (no pauses effectively, or fixed pauses)
    const { map, deltaMs, alertManager } = context;
    const alertData = alertManager.getAlertState(npc.id);

    if (alertData.state !== AlertState.PATROLLING) {
      super.update(npc, context);
      return;
    }

    if (!npc.data.patrolRoute || npc.data.patrolRoute.length === 0) return;

    const targetGrid = npc.data.patrolRoute[npc.currentPathIndex];
    const targetPos = gridToWorld(targetGrid.col, targetGrid.row);

    if (this.hasReached(npc.position, targetPos)) {
      // No wait time, continuous movement
      npc.currentPathIndex = (npc.currentPathIndex + 1) % npc.data.patrolRoute.length;
    } else {
      this.moveTo(npc, targetPos, deltaMs, map);
    }
  }
}

// ============================================================================
// Engine
// ============================================================================

export class PatrolEngine {
  private npcs: Map<string, NPCSimulationState> = new Map();
  private behaviors: Map<string, PatrolBehavior> = new Map();
  private alertManager: AlertManager;

  constructor(alertManager: AlertManager) {
    this.alertManager = alertManager;
  }

  registerNPC(id: string, initialPos: Point, data: NPCObjectData) {
    this.npcs.set(id, {
      id,
      position: initialPos,
      facing: data.facing || 'south',
      velocity: { x: 0, y: 0 },
      currentPathIndex: 0,
      waitTime: 0,
      data,
    });

    // Assign behavior based on faction
    let behavior: PatrolBehavior;
    switch (data.faction) {
      case 'steel_syndicate': // Lattice
        behavior = new SweepPatrol();
        break;
      case 'ember_colonies': // Ember
        behavior = new WanderPatrol();
        break;
      case 'ghost_protocol': // Ghost
        behavior = new StaticWatch();
        break;
      case 'covenant': // Covenant
        behavior = new RitualCircuit();
        break;
      default:
        behavior = new SimplePatrol();
    }
    this.behaviors.set(id, behavior);
  }

  tick(deltaMs: number, map: LocalMapTemplate, playerPos: Point, timeOfDay: string) {
    for (const [id, npc] of this.npcs) {
      const behavior = this.behaviors.get(id);
      
      // 1. Update Alert State
      this.alertManager.update(
        id, 
        npc.position, 
        npc.facing, 
        playerPos, 
        map, 
        deltaMs, 
        timeOfDay
      );

      // 2. Run Behavior
      if (behavior) {
        behavior.update(npc, {
          map,
          deltaMs,
          alertManager: this.alertManager,
          playerPos,
          timeOfDay
        });
      }
    }
  }

  getNPCState(id: string): NPCSimulationState | undefined {
    return this.npcs.get(id);
  }
  
  getAllNPCStates(): Map<string, NPCSimulationState> {
    return this.npcs;
  }
}
