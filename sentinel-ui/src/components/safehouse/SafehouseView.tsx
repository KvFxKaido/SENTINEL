/**
 * SafehouseView — Main safehouse component
 * 
 * The safehouse is the emotional anchor of the spatial layer.
 * A quiet place to account for what you still have.
 * 
 * Properties:
 * - No time pressure
 * - No surprise state changes
 * - No forced interactions
 * - Minimal ambient motion
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { SafehouseCanvas } from './SafehouseCanvas';
import { ObjectDetail } from './ObjectDetail';
import type { SafehouseState, PlacedObject } from './types';
import { getCampaignState, subscribeToEvents } from '../../lib/bridge';
import './safehouse.css';

interface SafehouseViewProps {
  /** Initial state (optional, will fetch if not provided) */
  initialState?: SafehouseState;
  /** Callback when player wants to leave safehouse */
  onExit?: () => void;
}

// Transform API response to SafehouseState
function transformApiState(apiState: unknown): SafehouseState {
  const state = apiState as Record<string, unknown>;
  const character = state.character as Record<string, unknown> | null;
  
  return {
    character: character ? {
      name: character.name as string,
      background: character.background as string,
      credits: character.credits as number,
      socialEnergy: character.social_energy as { current: number; max: number },
    } : null,
    gear: (character?.gear as Array<Record<string, unknown>> || []).map(g => ({
      id: g.id as string,
      name: g.name as string,
      category: g.category as string,
      description: g.description as string | undefined,
      used: g.used as boolean,
      singleUse: g.single_use as boolean | undefined,
    })),
    vehicles: ((state.vehicles || []) as Array<Record<string, unknown>>).map(v => ({
      id: v.id as string,
      name: v.name as string,
      type: v.type as string,
      description: v.description as string | undefined,
      fuel: v.fuel as number,
      condition: v.condition as number,
      status: v.status as SafehouseState['vehicles'][0]['status'],
      terrain: v.terrain as string[],
      capacity: v.capacity as number,
      cargo: v.cargo as boolean,
      stealth: v.stealth as boolean,
    })),
    enhancements: (character?.enhancements as Array<Record<string, unknown>> || []).map(e => ({
      id: e.id as string,
      name: e.name as string,
      source: e.source as string,
      benefit: e.benefit as string,
    })),
    threads: ((state.threads || []) as Array<Record<string, unknown>>).map(t => ({
      id: t.id as string,
      origin: t.origin as string,
      trigger: t.trigger as string,
      consequence: t.consequence as string,
      severity: t.severity as string,
      createdSession: t.created_session as number,
    })),
    region: state.region as string || 'Unknown',
    location: state.location as string || 'Unknown',
  };
}

export function SafehouseView({ initialState, onExit }: SafehouseViewProps) {
  const [state, setState] = useState<SafehouseState | null>(initialState || null);
  const [loading, setLoading] = useState(!initialState);
  const [error, setError] = useState<string | null>(null);
  const [selectedObject, setSelectedObject] = useState<PlacedObject | null>(null);
  const [hoveredObject, setHoveredObject] = useState<PlacedObject | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });

  // Fetch initial state
  useEffect(() => {
    if (initialState) return;

    async function fetchState() {
      try {
        setLoading(true);
        const apiState = await getCampaignState();
        if (apiState.ok) {
          setState(transformApiState(apiState));
        } else {
          setError('Failed to load safehouse state');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to connect');
      } finally {
        setLoading(false);
      }
    }

    fetchState();
  }, [initialState]);

  // Subscribe to SSE events for live updates
  useEffect(() => {
    const unsubscribe = subscribeToEvents((event) => {
      // Re-fetch state on relevant events
      if (
        event.event_type === 'state_changed' ||
        event.event_type === 'inventory_changed' ||
        event.event_type === 'turn_resolved'
      ) {
        getCampaignState().then(apiState => {
          if (apiState.ok) {
            setState(transformApiState(apiState));
          }
        });
      }
    });

    return unsubscribe;
  }, []);

  // Resize canvas to fit container
  useEffect(() => {
    function handleResize() {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      // Leave room for sidebar
      const sidebarWidth = selectedObject ? 320 : 0;
      const padding = 32;
      setCanvasSize({
        width: Math.max(600, rect.width - sidebarWidth - padding),
        height: Math.max(400, rect.height - padding),
      });
    }

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [selectedObject]);

  // Handle keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (selectedObject) {
          setSelectedObject(null);
        } else {
          onExit?.();
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedObject, onExit]);

  const handleObjectClick = useCallback((obj: PlacedObject) => {
    setSelectedObject(obj);
  }, []);

  const handleObjectHover = useCallback((obj: PlacedObject | null) => {
    setHoveredObject(obj);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedObject(null);
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="safehouse-container">
        <div className="safehouse-loading">
          <div className="loading-spinner" />
          <span>LOADING SAFEHOUSE...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="safehouse-container">
        <div className="safehouse-empty">
          <span>SAFEHOUSE UNAVAILABLE</span>
          <span style={{ fontSize: '12px' }}>{error}</span>
        </div>
      </div>
    );
  }

  // Empty state (no campaign loaded)
  if (!state) {
    return (
      <div className="safehouse-container">
        <div className="safehouse-empty">
          <span>NO CAMPAIGN LOADED</span>
          <span style={{ fontSize: '12px' }}>Start a campaign to access the safehouse</span>
        </div>
      </div>
    );
  }

  return (
    <div className="safehouse-container" ref={containerRef}>
      <div className="safehouse-canvas-wrapper">
        <SafehouseCanvas
          state={state}
          width={canvasSize.width}
          height={canvasSize.height}
          onObjectClick={handleObjectClick}
          onObjectHover={handleObjectHover}
        />
      </div>

      {selectedObject ? (
        <div className="safehouse-sidebar">
          <ObjectDetail
            object={selectedObject}
            state={state}
            onClose={handleCloseDetail}
          />
        </div>
      ) : (
        <div className="safehouse-sidebar">
          <div className="sidebar-empty">
            <div className="sidebar-empty-icon">🏠</div>
            <h3 className="sidebar-empty-title">Safehouse</h3>
            <p className="sidebar-empty-hint">
              Click on an item to inspect it.
              <br />
              Press ESC to return to the map.
            </p>
            {hoveredObject && (
              <p className="sidebar-empty-hint" style={{ marginTop: '16px', color: 'var(--accent-cyan)' }}>
                Hovering: {hoveredObject.label || hoveredObject.type}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
