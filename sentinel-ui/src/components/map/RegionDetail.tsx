import { useState } from 'react';
import type { Region, RegionConnectivity } from './types';
import { FACTION_INFO } from './types';

/**
 * RegionDetail — Panel showing region info and travel options.
 *
 * Displayed when a region is clicked on the world map.
 * Shows route feasibility and provides travel confirmation (commitment gate).
 *
 * The confirmation dialog is the key part of the commitment gate:
 * - Player sees full cost and consequences before committing
 * - Cancel at any point has zero side effects
 * - Only explicit confirmation triggers the travel action
 *
 * @see architecture/Sentinel 2D.md, Section 18.4 (Travel Action Sequence)
 */

interface RouteRequirement {
  type: string;
  faction?: string;
  min_standing?: string;
  vehicle_capability?: string;
  met: boolean;
}

interface RouteAlternative {
  type: string;
  description: string;
  cost?: Record<string, number>;
  consequence?: string;
  available: boolean;
}

interface RouteFromCurrent {
  from: string;
  to: string;
  requirements: RouteRequirement[];
  alternatives: RouteAlternative[];
  traversable: boolean;
  best_option: 'direct' | 'alternative' | 'blocked';
}

interface RegionInfo {
  id: string;
  name: string;
  description: string;
  primary_faction: string;
  contested_by: string[];
  terrain: string[];
  character: string;
  connectivity: RegionConnectivity;
  position: { x: number; y: number };
}

interface RegionDetailProps {
  region: RegionInfo;
  routes: RouteFromCurrent[];
  content: { npcs: string[]; jobs: string[]; threads: string[] };
  onTravel?: (regionId: string, via?: string) => void;
  onClose: () => void;
}

interface PendingTravel {
  regionId: string;
  via?: string;
  label: string;
  cost?: Record<string, number>;
  consequence?: string;
}

export function RegionDetail({
  region,
  routes,
  content,
  onTravel,
  onClose,
}: RegionDetailProps) {
  const [pendingTravel, setPendingTravel] = useState<PendingTravel | null>(null);
  
  const faction = FACTION_INFO[region.primary_faction as keyof typeof FACTION_INFO];
  const route = routes[0]; // Route from current region (if adjacent)

  // Handle travel selection - show confirmation
  const handleTravelSelect = (via?: string, label?: string, cost?: Record<string, number>, consequence?: string) => {
    setPendingTravel({
      regionId: region.id,
      via,
      label: label || 'Direct Route',
      cost,
      consequence,
    });
  };

  // Confirm travel - this is the commitment gate
  const handleConfirmTravel = () => {
    if (pendingTravel) {
      onTravel?.(pendingTravel.regionId, pendingTravel.via);
      setPendingTravel(null);
    }
  };

  // Cancel travel - zero side effects
  const handleCancelTravel = () => {
    setPendingTravel(null);
  };

  return (
    <div className="region-detail-panel terminal-text" style={{
      position: 'absolute',
      top: '16px',
      right: '16px',
      width: '360px',
      background: 'var(--bg-panel)',
      border: '1px solid var(--border-primary)',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
      backdropFilter: 'blur(8px)',
      zIndex: 40,
      maxHeight: 'calc(100vh - 120px)',
      overflowY: 'auto',
    }}>
      {/* Confirmation Dialog Overlay */}
      {pendingTravel && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.9)',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '24px',
          zIndex: 50,
        }}>
          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>
              CONFIRM TRAVEL
            </div>
            <div style={{ fontSize: '14px', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
              {region.name.toUpperCase()}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              via {pendingTravel.label}
            </div>
          </div>

          <div style={{ 
            background: 'var(--bg-tertiary)', 
            border: '1px solid var(--border-primary)',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '16px',
          }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
              This action will:
            </div>
            <div style={{ fontSize: '12px', color: 'var(--accent-amber)', marginBottom: '4px' }}>
              • Consume 1 turn
            </div>
            {pendingTravel.cost && Object.entries(pendingTravel.cost).map(([key, value]) => (
              <div key={key} style={{ fontSize: '12px', color: 'var(--accent-amber)', marginBottom: '4px' }}>
                • Cost: {key.replace(/_/g, ' ')} {value}
              </div>
            ))}
            {pendingTravel.consequence && (
              <div style={{ fontSize: '12px', color: 'var(--accent-red)' }}>
                • Risk: {pendingTravel.consequence.replace(/_/g, ' ')}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleCancelTravel}
              style={{
                flex: 1,
                padding: '10px',
                background: 'transparent',
                border: '1px solid var(--border-primary)',
                borderRadius: '4px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 'bold',
              }}
            >
              CANCEL
            </button>
            <button
              onClick={handleConfirmTravel}
              style={{
                flex: 1,
                padding: '10px',
                background: 'var(--accent-steel)',
                border: 'none',
                borderRadius: '4px',
                color: 'black',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 'bold',
              }}
            >
              CONFIRM
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)', letterSpacing: '0.05em', margin: 0 }}>
            {region.name.toUpperCase()}
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0' }}>
            {region.terrain.join(' / ').toUpperCase()}
          </p>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: '1px solid var(--border-primary)',
            borderRadius: '4px',
            color: 'var(--text-muted)',
            padding: '4px 8px',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          CLOSE
        </button>
      </div>

      {/* Faction */}
      {faction && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: faction.color }} />
          <span style={{ fontSize: '12px', color: faction.color }}>{faction.name.toUpperCase()}</span>
          <span style={{
            fontSize: '11px',
            padding: '1px 6px',
            borderRadius: '3px',
            border: '1px solid',
            color: connectivityColor(region.connectivity),
            borderColor: connectivityColor(region.connectivity),
          }}>
            {region.connectivity.toUpperCase()}
          </span>
        </div>
      )}

      {/* Description */}
      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '16px' }}>
        {region.description}
      </p>

      {/* Content summary */}
      {(content.npcs.length > 0 || content.jobs.length > 0 || content.threads.length > 0) && (
        <div style={{ marginBottom: '16px', padding: '8px', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
          {content.npcs.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-purple)', marginBottom: '4px' }}>
              NPCs: {content.npcs.join(', ')}
            </div>
          )}
          {content.jobs.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-green)', marginBottom: '4px' }}>
              Jobs: {content.jobs.join(', ')}
            </div>
          )}
          {content.threads.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-amber)' }}>
              Threads: {content.threads.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Travel options */}
      {route && (
        <div style={{ borderTop: '1px solid var(--border-primary)', paddingTop: '12px' }}>
          <h3 style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '8px' }}>
            TRAVEL OPTIONS
          </h3>

          {/* Direct route */}
          {route.requirements.length === 0 || route.requirements.every(r => r.met) ? (
            <TravelOption
              label="Direct Route"
              description="All requirements met"
              available={true}
              onSelect={() => handleTravelSelect(undefined, 'Direct Route')}
            />
          ) : (
            <div style={{ fontSize: '12px', marginBottom: '8px' }}>
              <div style={{ color: 'var(--accent-red)', marginBottom: '4px' }}>DIRECT ROUTE BLOCKED</div>
              {route.requirements.filter(r => !r.met).map((req, idx) => (
                <div key={idx} style={{ color: 'var(--text-muted)', paddingLeft: '8px' }}>
                  {'\u2717'} {formatRequirement(req)}
                </div>
              ))}
            </div>
          )}

          {/* Alternatives */}
          {route.alternatives.map((alt, idx) => (
            <TravelOption
              key={idx}
              label={alt.type.charAt(0).toUpperCase() + alt.type.slice(1)}
              description={alt.description}
              cost={alt.cost}
              consequence={alt.consequence}
              available={alt.available}
              onSelect={() => handleTravelSelect(alt.type, alt.type.charAt(0).toUpperCase() + alt.type.slice(1), alt.cost, alt.consequence)}
            />
          ))}

          {!route.traversable && (
            <div style={{ fontSize: '12px', color: 'var(--accent-red)', marginTop: '8px', padding: '8px', background: 'rgba(248,81,73,0.1)', borderRadius: '4px' }}>
              No viable route from current location.
            </div>
          )}
        </div>
      )}

      {!route && (
        <div style={{ borderTop: '1px solid var(--border-primary)', paddingTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
          Not adjacent to current region. Travel requires intermediate stops.
        </div>
      )}
    </div>
  );
}

function TravelOption({
  label,
  description,
  cost,
  consequence,
  available,
  onSelect,
}: {
  label: string;
  description: string;
  cost?: Record<string, number>;
  consequence?: string;
  available: boolean;
  onSelect: () => void;
}) {
  return (
    <div style={{
      padding: '8px',
      marginBottom: '6px',
      background: 'var(--bg-tertiary)',
      border: `1px solid ${available ? 'var(--border-primary)' : 'var(--border-secondary)'}`,
      borderRadius: '4px',
      opacity: available ? 1 : 0.5,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', fontWeight: 'bold', color: available ? 'var(--text-primary)' : 'var(--text-muted)' }}>
          {label}
        </span>
        {available && (
          <button
            onClick={onSelect}
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              background: 'var(--accent-steel)',
              color: 'black',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            SELECT
          </button>
        )}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
        {description}
      </div>
      {cost && (
        <div style={{ fontSize: '11px', color: 'var(--accent-amber)', marginTop: '4px' }}>
          Cost: {Object.entries(cost).map(([k, v]) => `${k.replace('_', ' ')} ${v}`).join(', ')}
        </div>
      )}
      {consequence && (
        <div style={{ fontSize: '11px', color: 'var(--accent-red)', marginTop: '2px' }}>
          Risk: {consequence.replace(/_/g, ' ')}
        </div>
      )}
    </div>
  );
}

function connectivityColor(connectivity: RegionConnectivity): string {
  switch (connectivity) {
    case 'disconnected': return 'var(--text-muted)';
    case 'aware': return 'var(--state-aware)';
    case 'connected': return 'var(--state-connected)';
    case 'embedded': return 'var(--state-embedded)';
    default: return 'var(--text-muted)';
  }
}

function formatRequirement(req: { type: string; faction?: string; min_standing?: string; vehicle_capability?: string }): string {
  if (req.type === 'faction' && req.faction) {
    const faction = FACTION_INFO[req.faction as keyof typeof FACTION_INFO];
    return `${faction?.name || req.faction} standing: ${req.min_standing || 'neutral'}`;
  }
  if (req.type === 'vehicle') {
    return `Vehicle with ${req.vehicle_capability || 'capability'} required`;
  }
  return `${req.type} requirement`;
}

export default RegionDetail;
