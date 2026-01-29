/**
 * OverworldView — Main overworld component
 * 
 * The overworld makes distance, exposure, and hesitation legible.
 * Movement is free but non-authoritative — proximity alone never commits.
 * 
 * Interaction Pattern:
 * Proximity → Prompt → Explicit Confirmation → Commitment Gate → Resolution
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { OverworldCanvas } from './OverworldCanvas';
import { InteractionPanel } from './InteractionPanel';
import type {
  OverworldState,
  Entity,
  RegionData,
  TerrainType,
  NPCData,
  HazardData,
  POIData,
  ExitData,
} from './types';
import {
  HAZARD_TEMPLATES,
  POI_TEMPLATES,
  PLAYER_RADIUS,
} from './types';
import { getCampaignState, getRegionDetail, sendCommand, subscribeToEvents } from '../../lib/bridge';
import './overworld.css';

interface OverworldViewProps {
  onExit?: () => void;
  onTravel?: (regionId: string) => void;
}

// ============================================================================
// Procedural Generation
// ============================================================================

function generateEntities(
  region: RegionData,
  npcs: Array<{ id: string; name: string; faction: string | null; disposition: string; status: string }>,
  canvasWidth: number,
  canvasHeight: number
): Entity[] {
  const entities: Entity[] = [];
  const usedPositions: Array<{ x: number; y: number; radius: number }> = [];

  // Helper to find non-overlapping position
  function findPosition(radius: number): { x: number; y: number } {
    const margin = 60;
    const maxAttempts = 50;
    
    for (let i = 0; i < maxAttempts; i++) {
      const x = margin + Math.random() * (canvasWidth - margin * 2);
      const y = margin + 40 + Math.random() * (canvasHeight - margin * 2 - 40); // Account for header
      
      const overlaps = usedPositions.some(pos => {
        const dx = pos.x - x;
        const dy = pos.y - y;
        const minDist = pos.radius + radius + 30;
        return Math.sqrt(dx * dx + dy * dy) < minDist;
      });
      
      if (!overlaps) {
        usedPositions.push({ x, y, radius });
        return { x, y };
      }
    }
    
    // Fallback to random position
    return {
      x: margin + Math.random() * (canvasWidth - margin * 2),
      y: margin + 40 + Math.random() * (canvasHeight - margin * 2 - 40),
    };
  }

  // Add NPCs
  for (const npc of npcs.filter(n => n.status === 'active')) {
    const position = findPosition(16);
    entities.push({
      id: `npc-${npc.id}`,
      type: 'npc',
      position,
      radius: 16,
      label: npc.name,
      data: {
        name: npc.name,
        faction: npc.faction,
        disposition: npc.disposition,
        status: npc.status as 'active' | 'dormant',
      } as NPCData,
    });
  }

  // Generate hazards based on terrain
  const primaryTerrain = region.terrain[0] as TerrainType || 'urban';
  const hazardTemplates = HAZARD_TEMPLATES[primaryTerrain] || HAZARD_TEMPLATES.urban;
  const numHazards = Math.floor(Math.random() * 2) + 1;

  for (let i = 0; i < numHazards; i++) {
    const position = findPosition(20);
    const hazardName = hazardTemplates[Math.floor(Math.random() * hazardTemplates.length)];
    const severities: Array<'minor' | 'moderate' | 'major'> = ['minor', 'moderate', 'major'];
    
    entities.push({
      id: `hazard-${i}`,
      type: 'hazard',
      position,
      radius: 20,
      label: hazardName,
      data: {
        name: hazardName,
        severity: severities[Math.floor(Math.random() * severities.length)],
        terrain: primaryTerrain,
      } as HazardData,
    });
  }

  // Generate POIs
  const poiTemplates = POI_TEMPLATES[primaryTerrain] || POI_TEMPLATES.urban;
  const numPOIs = Math.floor(Math.random() * 3) + 1;

  for (let i = 0; i < numPOIs; i++) {
    const position = findPosition(14);
    const poiName = poiTemplates[Math.floor(Math.random() * poiTemplates.length)];
    
    entities.push({
      id: `poi-${i}`,
      type: 'poi',
      position,
      radius: 14,
      label: poiName,
      data: {
        name: poiName,
        description: `A ${poiName.toLowerCase()} in the ${region.name}.`,
        interactable: Math.random() > 0.5,
      } as POIData,
    });
  }

  return entities;
}

function generateExits(
  regionId: string,
  routes: Array<{ to: string; traversable: boolean; blocked_reason?: string }>,
  canvasWidth: number,
  canvasHeight: number
): Entity[] {
  const exits: Entity[] = [];
  const directions: Array<{ dir: 'north' | 'south' | 'east' | 'west'; x: number; y: number }> = [
    { dir: 'north', x: canvasWidth / 2, y: 50 },
    { dir: 'south', x: canvasWidth / 2, y: canvasHeight - 30 },
    { dir: 'east', x: canvasWidth - 30, y: canvasHeight / 2 },
    { dir: 'west', x: 30, y: canvasHeight / 2 },
  ];

  routes.forEach((route, index) => {
    const dirInfo = directions[index % directions.length];
    
    exits.push({
      id: `exit-${route.to}`,
      type: 'exit',
      position: { x: dirInfo.x, y: dirInfo.y },
      radius: 18,
      label: route.to.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      data: {
        targetRegion: route.to,
        direction: dirInfo.dir,
        traversable: route.traversable,
        blocked_reason: route.blocked_reason,
      } as ExitData,
    });
  });

  return exits;
}

// ============================================================================
// Component
// ============================================================================

export function OverworldView({ onExit, onTravel }: OverworldViewProps) {
  const [state, setState] = useState<OverworldState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });

  // Fetch initial state
  useEffect(() => {
    async function fetchState() {
      try {
        setLoading(true);
        
        // Get campaign state for NPCs and current region
        const campaignState = await getCampaignState();
        if (!campaignState.ok) {
          setError('Failed to load campaign state');
          return;
        }

        // Get region details
        const regionId = campaignState.region || 'rust_corridor';
        let regionDetail;
        try {
          regionDetail = await getRegionDetail(regionId);
        } catch {
          // Use fallback data if region detail fails
          regionDetail = {
            ok: true,
            region: {
              id: regionId,
              name: regionId.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
              description: 'A region in the wasteland.',
              primary_faction: 'unknown',
              contested_by: [],
              terrain: ['urban'],
              character: 'Unknown territory.',
              connectivity: 'aware',
              position: { x: 50, y: 50 },
            },
            routes_from_current: [],
            content: { npcs: [], jobs: [], threads: [] },
          };
        }

        const region: RegionData = {
          id: regionDetail.region.id,
          name: regionDetail.region.name,
          description: regionDetail.region.description,
          terrain: regionDetail.region.terrain as TerrainType[],
          primaryFaction: regionDetail.region.primary_faction,
          character: regionDetail.region.character,
        };

        // Generate entities
        const entities = generateEntities(
          region,
          campaignState.npcs || [],
          canvasSize.width,
          canvasSize.height
        );

        // Generate exits from routes
        const exits = generateExits(
          regionId,
          regionDetail.routes_from_current?.map((r: { to: string; traversable: boolean }) => ({
            to: r.to,
            traversable: r.traversable,
          })) || [],
          canvasSize.width,
          canvasSize.height
        );

        setState({
          region,
          player: {
            position: { x: canvasSize.width / 2, y: canvasSize.height / 2 },
            name: campaignState.character?.name || 'Agent',
          },
          entities,
          exits,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to connect');
      } finally {
        setLoading(false);
      }
    }

    fetchState();
  }, [canvasSize.width, canvasSize.height]);

  // Subscribe to SSE events
  useEffect(() => {
    const unsubscribe = subscribeToEvents((event) => {
      if (
        event.event_type === 'map.region_changed' ||
        event.event_type === 'state_changed'
      ) {
        // Refresh state on region change
        window.location.reload();
      }
    });

    return unsubscribe;
  }, []);

  // Resize canvas
  useEffect(() => {
    function handleResize() {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const sidebarWidth = selectedEntity ? 320 : 0;
      setCanvasSize({
        width: Math.max(600, rect.width - sidebarWidth),
        height: Math.max(400, rect.height),
      });
    }

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [selectedEntity]);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (selectedEntity) {
          setSelectedEntity(null);
        } else {
          onExit?.();
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedEntity, onExit]);

  const handleEntityInteract = useCallback((entity: Entity) => {
    setSelectedEntity(entity);
  }, []);

  const handleExitApproach = useCallback((entity: Entity) => {
    // Show exit in sidebar when approached
    setSelectedEntity(entity);
  }, []);

  const handleAction = useCallback(async (action: string, params?: Record<string, unknown>) => {
    if (!selectedEntity) return;

    // Handle travel action
    if (action === 'travel' && selectedEntity.type === 'exit') {
      const exitData = selectedEntity.data as ExitData;
      try {
        await sendCommand('slash', { command: 'travel', args: [exitData.targetRegion] });
        onTravel?.(exitData.targetRegion);
      } catch (err) {
        console.error('Travel failed:', err);
      }
    }

    // Other actions would be handled here
    console.log('Action:', action, 'Entity:', selectedEntity.id, 'Params:', params);
  }, [selectedEntity, onTravel]);

  const handleClosePanel = useCallback(() => {
    setSelectedEntity(null);
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="overworld-container">
        <div className="overworld-loading">
          <div className="loading-spinner" />
          <span>LOADING REGION...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !state) {
    return (
      <div className="overworld-container">
        <div className="overworld-error">
          <span>REGION UNAVAILABLE</span>
          <span style={{ fontSize: '12px' }}>{error || 'No data'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="overworld-container" ref={containerRef}>
      <div className="overworld-canvas-wrapper">
        <OverworldCanvas
          state={state}
          width={canvasSize.width}
          height={canvasSize.height}
          onEntityInteract={handleEntityInteract}
          onExitApproach={handleExitApproach}
        />
      </div>

      {selectedEntity ? (
        <div className="overworld-sidebar">
          <InteractionPanel
            entity={selectedEntity}
            onAction={handleAction}
            onClose={handleClosePanel}
          />
        </div>
      ) : (
        <div className="overworld-sidebar">
          <div className="sidebar-empty">
            <div className="sidebar-empty-icon">🗺️</div>
            <h3 className="sidebar-empty-title">{state.region.name}</h3>
            <p className="sidebar-empty-hint">
              Move with WASD or arrow keys.
              <br />
              Approach entities to interact.
            </p>
            <div className="controls-hint">
              <div className="control-row">
                <span className="control-key">WASD / Arrows</span>
                <span className="control-action">Move</span>
              </div>
              <div className="control-row">
                <span className="control-key">E</span>
                <span className="control-action">Interact</span>
              </div>
              <div className="control-row">
                <span className="control-key">ESC</span>
                <span className="control-action">Exit</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
