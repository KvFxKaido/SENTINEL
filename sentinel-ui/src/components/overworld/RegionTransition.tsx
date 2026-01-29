/**
 * RegionTransition — Handles seamless region transitions
 * 
 * When the player travels to a new region, this component:
 * 1. Shows a transition overlay
 * 2. Loads the new region data
 * 3. Fades into the new region
 */

import { useEffect, useState } from 'react';
import type { RegionTransition as TransitionType, TransitionState } from './expansion-types';
import './overworld.css';

interface RegionTransitionProps {
  transition: TransitionType | null;
  onComplete: () => void;
}

export function RegionTransition({ transition, onComplete }: RegionTransitionProps) {
  const [state, setState] = useState<TransitionState>({
    isTransitioning: false,
    progress: 0,
    transition: null,
  });

  useEffect(() => {
    if (!transition) {
      setState({ isTransitioning: false, progress: 0, transition: null });
      return;
    }

    setState({ isTransitioning: true, progress: 0, transition });

    // Animate progress
    const duration = 1500; // 1.5 seconds
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min((elapsed / duration) * 100, 100);

      setState(prev => ({ ...prev, progress }));

      if (progress < 100) {
        requestAnimationFrame(animate);
      } else {
        // Transition complete
        setTimeout(() => {
          onComplete();
        }, 200);
      }
    };

    requestAnimationFrame(animate);
  }, [transition, onComplete]);

  if (!state.isTransitioning || !state.transition) {
    return null;
  }

  const directionLabel = {
    north: 'NORTH',
    south: 'SOUTH',
    east: 'EAST',
    west: 'WEST',
  }[state.transition.direction];

  return (
    <div className="region-transition-overlay">
      <div className="transition-content">
        <div className="transition-direction">{directionLabel}</div>
        <div className="transition-arrow">
          {state.transition.direction === 'north' && '↑'}
          {state.transition.direction === 'south' && '↓'}
          {state.transition.direction === 'east' && '→'}
          {state.transition.direction === 'west' && '←'}
        </div>
        <div className="transition-destination">
          {state.transition.toRegion.replace(/_/g, ' ').toUpperCase()}
        </div>
        <div className="transition-progress-bar">
          <div 
            className="transition-progress-fill" 
            style={{ width: `${state.progress}%` }}
          />
        </div>
        <div className="transition-cost">
          COST: {state.transition.cost} TURN{state.transition.cost !== 1 ? 'S' : ''}
        </div>
        {state.transition.consequence && (
          <div className="transition-consequence">
            {state.transition.consequence}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Mini-map Component
// ============================================================================

interface MiniMapProps {
  currentRegion: string;
  connectedRegions: Array<{
    id: string;
    name: string;
    direction: 'north' | 'south' | 'east' | 'west';
    traversable: boolean;
  }>;
  onRegionClick?: (regionId: string) => void;
}

export function MiniMap({ currentRegion, connectedRegions, onRegionClick }: MiniMapProps) {
  // Position offsets for each direction
  const directionOffsets = {
    north: { x: 50, y: 10 },
    south: { x: 50, y: 90 },
    east: { x: 90, y: 50 },
    west: { x: 10, y: 50 },
  };

  return (
    <div className="mini-map">
      <div className="mini-map-title">REGION</div>
      <div className="mini-map-content">
        {/* Current region in center */}
        <div 
          className="mini-map-region mini-map-current"
          style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
        >
          <span className="region-dot current" />
          <span className="region-name">{currentRegion.replace(/_/g, ' ')}</span>
        </div>

        {/* Connected regions */}
        {connectedRegions.map(region => {
          const offset = directionOffsets[region.direction];
          return (
            <div
              key={region.id}
              className={`mini-map-region ${region.traversable ? 'traversable' : 'blocked'}`}
              style={{ left: `${offset.x}%`, top: `${offset.y}%`, transform: 'translate(-50%, -50%)' }}
              onClick={() => region.traversable && onRegionClick?.(region.id)}
            >
              <span className={`region-dot ${region.traversable ? 'open' : 'blocked'}`} />
              <span className="region-name">{region.name.replace(/_/g, ' ')}</span>
            </div>
          );
        })}

        {/* Connection lines */}
        <svg className="mini-map-connections" viewBox="0 0 100 100">
          {connectedRegions.map(region => {
            const offset = directionOffsets[region.direction];
            return (
              <line
                key={region.id}
                x1="50"
                y1="50"
                x2={offset.x}
                y2={offset.y}
                className={region.traversable ? 'connection-open' : 'connection-blocked'}
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}
