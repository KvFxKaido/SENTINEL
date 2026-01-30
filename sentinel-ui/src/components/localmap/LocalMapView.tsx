/**
 * LocalMapView — Main local map component (Phase 2)
 * 
 * Wraps LocalMapCanvas with state management, interaction panels,
 * and map transitions.
 * 
 * This is the primary exploration interface for Phase 2.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { LocalMapCanvas } from './LocalMapCanvas';
import { getMapTemplate, getSpawnPoint } from './maps';
import { gridToWorld } from './collision';
import { useGameClock, formatTimeShort, getTimeOfDay, getAmbientLightForTime } from './useGameClock';
import type { 
  LocalMapTemplate, 
  MapObject, 
  MapExit, 
  Point, 
  GridPosition,
} from './types';
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
}

// ============================================================================
// Interaction Panel Component
// ============================================================================

function InteractionPanel({ target, type, onAction, onClose }: InteractionPanelProps) {
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

  return (
    <div className="localmap-panel">
      <div className="panel-header">
        <h3 className="panel-title">
          {isExit ? exit?.label : obj?.name}
        </h3>
        <button className="panel-close" onClick={onClose}>×</button>
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
                  onClick={() => onAction('travel', { exitId: exit.id })}
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
                onClick={() => onAction('talk', { npcId: (obj.data as { npcId?: string })?.npcId })}
              >
                Talk
              </button>
              <button 
                className="action-button action-secondary"
                onClick={() => onAction('observe', { objectId: obj.id })}
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
                  onClick={() => onAction('use', { objectId: obj.id })}
                >
                  {(obj.data as { propType?: string })?.propType === 'container' ? 'Open' : 'Use'}
                </button>
              )}
              <button 
                className="action-button action-secondary"
                onClick={() => onAction('examine', { objectId: obj.id })}
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
                onClick={() => onAction('pickup', { itemId: (obj.data as { itemId?: string })?.itemId })}
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
  const [currentMap, setCurrentMap] = useState<LocalMapTemplate | null>(null);
  const [spawnPosition, setSpawnPosition] = useState<Point | null>(null);
  const [spawnFacing, setSpawnFacing] = useState<'north' | 'south' | 'east' | 'west'>('south');
  
  const [selectedTarget, setSelectedTarget] = useState<MapObject | MapExit | null>(null);
  const [selectedType, setSelectedType] = useState<'object' | 'exit' | null>(null);
  const [paused, setPaused] = useState(false);
  
  // Game clock - pauses during interactions and transitions
  const [clockState, clockActions] = useGameClock({
    initialTime,
    autoAdvance: true,
    onTimeChange: (time) => onTimeChange?.(time),
  });
  
  // Pause clock when interacting or paused
  useEffect(() => {
    if (paused || selectedTarget) {
      clockActions.pause(paused ? 'menu' : 'interaction');
    } else {
      clockActions.resume();
    }
  }, [paused, selectedTarget, clockActions]);
  
  const [transition, setTransition] = useState<{
    from: string;
    to: string;
    direction: string;
    targetSpawn: string;
  } | null>(null);
  
  const [playerGridPos, setPlayerGridPos] = useState<GridPosition>({ col: 0, row: 0 });
  
  const containerRef = useRef<HTMLDivElement>(null);

  // Load map
  useEffect(() => {
    const map = getMapTemplate(currentMapId);
    if (map) {
      setCurrentMap(map);
      
      // Get spawn position
      const spawn = getSpawnPoint(currentMapId, initialSpawnId || 'default');
      if (spawn) {
        setSpawnPosition(gridToWorld(spawn.col, spawn.row));
        setSpawnFacing(spawn.facing as typeof spawnFacing);
      }
      
      onMapChange?.(currentMapId);
    }
  }, [currentMapId, initialSpawnId, onMapChange]);

  // Handle exit approach
  const handleExitApproach = useCallback((exit: MapExit) => {
    setSelectedTarget(exit);
    setSelectedType('exit');
  }, []);

  // Handle object interaction
  const handleObjectInteract = useCallback((obj: MapObject) => {
    setSelectedTarget(obj);
    setSelectedType('object');
    onInteraction?.('select', obj);
  }, [onInteraction]);

  // Handle position change
  const handlePositionChange = useCallback((pos: Point, gridPos: GridPosition) => {
    setPlayerGridPos(gridPos);
  }, []);

  // Handle panel action
  const handleAction = useCallback((action: string, params?: Record<string, unknown>) => {
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
    } else {
      onInteraction?.(action, selectedTarget as MapObject | MapExit);
    }
  }, [currentMapId, selectedTarget, selectedType, onInteraction]);

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
        if (selectedTarget) {
          handleClosePanel();
        } else {
          setPaused(p => !p);
          onExit?.();
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedTarget, handleClosePanel, onExit]);

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
            initialPosition={spawnPosition || undefined}
            initialFacing={spawnFacing}
            onExitApproach={handleExitApproach}
            onObjectInteract={handleObjectInteract}
            onPositionChange={handlePositionChange}
            paused={paused || !!transition}
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
      </div>

      <div className="localmap-sidebar">
        <InteractionPanel
          target={selectedTarget}
          type={selectedType}
          onAction={handleAction}
          onClose={handleClosePanel}
        />
      </div>

      {/* Pause overlay */}
      {paused && !transition && (
        <div className="localmap-pause-overlay">
          <div className="pause-menu">
            <h2>PAUSED</h2>
            <button onClick={() => setPaused(false)}>Resume</button>
            <button onClick={onExit}>Exit to Menu</button>
          </div>
        </div>
      )}
    </div>
  );
}
