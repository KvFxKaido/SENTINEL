import { useEffect, useRef, useState, useMemo } from 'react';
import type { LocalMapTemplate, Point, NPCObjectData } from './types';
import { gridToWorld } from './collision';
import { PatrolEngine, type NPCSimulationState } from './patrol';
import { AlertManager, AlertState } from './alertSystem';
import { getTimeOfDay, type GameTime } from './useGameClock';

export interface SimulatedNPC {
  id: string;
  position: Point;
  facing: 'north' | 'south' | 'east' | 'west';
  alertState: AlertState;
  alertLevel: number;
  data: NPCObjectData;
}

export function usePatrolSimulation(
  map: LocalMapTemplate,
  playerPos: Point,
  gameTime: GameTime,
  paused: boolean = false
) {
  const alertManagerRef = useRef<AlertManager>(new AlertManager());
  const engineRef = useRef<PatrolEngine>(new PatrolEngine(alertManagerRef.current));
  const [npcStates, setNpcStates] = useState<Map<string, SimulatedNPC>>(new Map());
  const lastTimeRef = useRef<number>(0);
  const rafRef = useRef<number>(0);

  // Initialize Simulation
  useEffect(() => {
    // Reset engine on map change
    alertManagerRef.current = new AlertManager();
    engineRef.current = new PatrolEngine(alertManagerRef.current);
    
    // Register NPCs
    for (const obj of map.objects) {
      if (obj.type === 'npc' && obj.data) {
        const initialPos = gridToWorld(obj.position.col, obj.position.row);
        engineRef.current.registerNPC(obj.id, initialPos, obj.data as NPCObjectData);
      }
    }
  }, [map.id]); // Re-init when map ID changes

  const npcSignature = useMemo(() => {
    return map.objects
      .filter(obj => obj.type === 'npc' && obj.data)
      .map(obj => {
        const data = obj.data as NPCObjectData;
        return `${obj.id}:${data.disposition || 'neutral'}:${data.faction || 'none'}`;
      })
      .join('|');
  }, [map.objects]);

  useEffect(() => {
    const engine = engineRef.current;
    for (const obj of map.objects) {
      if (obj.type === 'npc' && obj.data) {
        engine.updateNPCData(obj.id, obj.data as NPCObjectData);
      }
    }
  }, [npcSignature, map.objects]);

  // Simulation Loop
  useEffect(() => {
    if (paused) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      lastTimeRef.current = 0;
      return;
    }

    const loop = (timestamp: number) => {
      if (!lastTimeRef.current) {
        lastTimeRef.current = timestamp;
        rafRef.current = requestAnimationFrame(loop);
        return;
      }

      const deltaMs = timestamp - lastTimeRef.current;
      lastTimeRef.current = timestamp;

      // Cap delta to avoid huge jumps on tab switch
      const safeDelta = Math.min(deltaMs, 100);

      const timeOfDay = getTimeOfDay(gameTime.hour);
      
      engineRef.current.tick(safeDelta, map, playerPos, timeOfDay);

      // Sync state to React for rendering
      // We throttle this slightly or just sync every frame if performance allows
      // For ~10 NPCs, every frame is fine.
      const newStates = new Map<string, SimulatedNPC>();
      const engineStates = engineRef.current.getAllNPCStates();

      for (const [id, simState] of engineStates) {
        const alertData = alertManagerRef.current.getAlertState(id);
        newStates.set(id, {
          id,
          position: simState.position,
          facing: simState.facing,
          alertState: alertData.state,
          alertLevel: alertData.alertLevel,
          data: simState.data,
        });
      }

      setNpcStates(newStates);

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [map, paused, playerPos, gameTime]);

  return npcStates;
}
