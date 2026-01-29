import type { RegionData, RegionConnectivity, ContentMarker } from './types';
import { FACTION_INFO } from './types';

interface MapTooltipProps {
  region: RegionData;
  connectivity: RegionConnectivity;
  markers: ContentMarker[];
  mousePosition: { x: number; y: number };
}

const getConnectivityText = (connectivity: RegionConnectivity): string => {
  switch (connectivity) {
    case 'disconnected': return 'DISCONNECTED';
    case 'aware': return 'AWARE';
    case 'connected': return 'CONNECTED';
    case 'embedded': return 'EMBEDDED';
    default: return 'UNKNOWN';
  }
};

const getConnectivityColor = (connectivity: RegionConnectivity): string => {
  switch (connectivity) {
    case 'disconnected': return 'var(--text-muted)';
    case 'aware': return 'var(--state-aware)';
    case 'connected': return 'var(--state-connected)';
    case 'embedded': return 'var(--state-embedded)';
    default: return 'var(--text-muted)';
  }
};

export function MapTooltip({
  region,
  connectivity,
  markers,
  mousePosition,
}: MapTooltipProps) {
  const faction = FACTION_INFO[region.primary_faction];
  const npcCount = markers.filter(m => m.type === 'npc').reduce((sum, m) => sum + (m.count || 1), 0);
  const hasJob = markers.some(m => m.type === 'job');
  const hasThread = markers.some(m => m.type === 'thread');

  const tooltipWidth = 320;
  const tooltipHeight = 300;
  const padding = 20;

  let left = mousePosition.x + padding;
  let top = mousePosition.y + padding;

  if (typeof window !== 'undefined') {
    if (left + tooltipWidth > window.innerWidth) {
      left = mousePosition.x - tooltipWidth - padding;
    }
    if (top + tooltipHeight > window.innerHeight) {
      top = mousePosition.y - tooltipHeight - padding;
    }
  }

  return (
    <div
      className="fixed z-50 map-tooltip terminal-text"
      style={{ left, top, maxWidth: 320 }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'var(--text-primary)', letterSpacing: '0.05em', margin: 0 }}>
            {region.name.toUpperCase()}
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px', margin: 0 }}>
            {region.terrain.join(' / ').toUpperCase()}
          </p>
        </div>
        <span
          style={{
            fontSize: '12px',
            padding: '2px 8px',
            borderRadius: '4px',
            border: '1px solid',
            color: getConnectivityColor(connectivity),
            borderColor: getConnectivityColor(connectivity),
            opacity: 0.8,
          }}
        >
          {getConnectivityText(connectivity)}
        </span>
      </div>

      {/* Faction info */}
      {faction && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', paddingBottom: '12px', borderBottom: '1px solid var(--border-secondary)' }}>
          <div
            style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: faction.color }}
          />
          <span style={{ fontSize: '12px', color: faction.color }}>
            {faction.name.toUpperCase()}
          </span>
          {region.contested_by && region.contested_by.length > 0 && (
            <span style={{ fontSize: '12px', color: 'var(--accent-amber)' }}>
              (CONTESTED)
            </span>
          )}
        </div>
      )}

      {/* Description */}
      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '12px' }}>
        {region.description}
      </p>

      {/* Character quote */}
      <p style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: '12px', borderLeft: '2px solid var(--border-primary)', paddingLeft: '8px' }}>
        &ldquo;{region.character}&rdquo;
      </p>

      {/* Content markers */}
      {(npcCount > 0 || hasJob || hasThread) && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px', paddingBottom: '12px', borderBottom: '1px solid var(--border-secondary)' }}>
          {hasJob && (
            <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'rgba(126,231,135,0.2)', color: 'var(--accent-green)' }}>
              JOB AVAILABLE
            </span>
          )}
          {hasThread && (
            <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,166,87,0.2)', color: 'var(--accent-amber)' }}>
              DORMANT THREAD
            </span>
          )}
          {npcCount > 0 && (
            <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'rgba(210,168,255,0.2)', color: 'var(--accent-purple)' }}>
              {npcCount} NPC{npcCount > 1 ? 'S' : ''}
            </span>
          )}
        </div>
      )}

      {/* Routes */}
      {region.routes && region.routes.length > 0 && connectivity !== 'disconnected' && (
        <div style={{ marginBottom: '12px' }}>
          <h4 style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.05em' }}>
            CONNECTED REGIONS
          </h4>
          <div>
            {region.routes.slice(0, 4).map((route, idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {'\u2192'} {route.to.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {route.requirements.length === 0 ? 'OPEN' :
                   route.contested ? 'CONTESTED' : 'RESTRICTED'}
                </span>
              </div>
            ))}
            {region.routes.length > 4 && (
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                +{region.routes.length - 4} more...
              </span>
            )}
          </div>
        </div>
      )}

      {/* Points of interest */}
      {connectivity === 'embedded' && region.points_of_interest && region.points_of_interest.length > 0 && (
        <div>
          <h4 style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.05em' }}>
            POINTS OF INTEREST
          </h4>
          {region.points_of_interest.slice(0, 3).map((poi, idx) => (
            <div key={idx} style={{ fontSize: '12px', color: 'var(--accent-steel)' }}>
              {'\u2022'} {poi}
            </div>
          ))}
        </div>
      )}

      {/* Nexus presence indicator */}
      <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>NEXUS PRESENCE</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {[1, 2, 3].map((level) => (
            <div
              key={level}
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '2px',
                backgroundColor: level <= (region.nexus_presence === 'high' ? 3 : region.nexus_presence === 'medium' ? 2 : 1)
                  ? 'var(--faction-nexus)'
                  : 'var(--border-secondary)',
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default MapTooltip;
