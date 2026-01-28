import type { RegionData, RegionConnectivity, ContentMarker } from '@/types/map';
import { factions } from '@/data/factions';

interface MapTooltipProps {
  region: RegionData;
  connectivity: RegionConnectivity;
  markers: ContentMarker[];
  mousePosition: { x: number; y: number };
}

// Get connectivity display text
const getConnectivityText = (connectivity: RegionConnectivity): string => {
  switch (connectivity) {
    case 'disconnected':
      return 'DISCONNECTED';
    case 'aware':
      return 'AWARE';
    case 'connected':
      return 'CONNECTED';
    case 'embedded':
      return 'EMBEDDED';
    default:
      return 'UNKNOWN';
  }
};

// Get connectivity color
const getConnectivityColor = (connectivity: RegionConnectivity): string => {
  switch (connectivity) {
    case 'disconnected':
      return 'var(--text-muted)';
    case 'aware':
      return 'var(--state-aware)';
    case 'connected':
      return 'var(--state-connected)';
    case 'embedded':
      return 'var(--state-embedded)';
    default:
      return 'var(--text-muted)';
  }
};

export const MapTooltip = ({
  region,
  connectivity,
  markers,
  mousePosition,
}: MapTooltipProps) => {
  const faction = factions[region.primaryFaction];
  const npcCount = markers.filter(m => m.type === 'npc').reduce((sum, m) => sum + (m.count || 1), 0);
  const hasJob = markers.some(m => m.type === 'job');
  const hasThread = markers.some(m => m.type === 'thread');

  // Calculate tooltip position to keep it on screen
  const tooltipWidth = 320;
  const tooltipHeight = 300;
  const padding = 20;
  
  let left = mousePosition.x + padding;
  let top = mousePosition.y + padding;
  
  // Adjust if going off screen
  if (left + tooltipWidth > window.innerWidth) {
    left = mousePosition.x - tooltipWidth - padding;
  }
  if (top + tooltipHeight > window.innerHeight) {
    top = mousePosition.y - tooltipHeight - padding;
  }

  return (
    <div
      className="fixed z-50 map-tooltip terminal-text"
      style={{
        left,
        top,
        maxWidth: 320,
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold text-[var(--text-primary)] tracking-wider">
            {region.name.toUpperCase()}
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            {region.terrain.join(' / ').toUpperCase()}
          </p>
        </div>
        <span 
          className="text-xs px-2 py-0.5 rounded border"
          style={{ 
            color: getConnectivityColor(connectivity),
            borderColor: getConnectivityColor(connectivity),
            opacity: 0.8,
          }}
        >
          {getConnectivityText(connectivity)}
        </span>
      </div>

      {/* Faction info */}
      <div className="flex items-center gap-2 mb-3 pb-3 border-b border-[var(--border-secondary)]">
        <div 
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: faction.color }}
        />
        <span className="text-xs" style={{ color: faction.color }}>
          {faction.name.toUpperCase()}
        </span>
        {region.contestedBy && region.contestedBy.length > 0 && (
          <span className="text-xs text-[var(--accent-amber)]">
            (CONTESTED)
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-3">
        {region.description}
      </p>

      {/* Character quote */}
      <p className="text-xs text-[var(--text-muted)] italic mb-3 border-l-2 border-[var(--border-primary)] pl-2">
        &ldquo;{region.character}&rdquo;
      </p>

      {/* Content markers */}
      {(npcCount > 0 || hasJob || hasThread) && (
        <div className="flex flex-wrap gap-2 mb-3 pb-3 border-b border-[var(--border-secondary)]">
          {hasJob && (
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--accent-green)]/20 text-[var(--accent-green)]">
              ◆ JOB AVAILABLE
            </span>
          )}
          {hasThread && (
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]">
              ⚡ DORMANT THREAD
            </span>
          )}
          {npcCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--accent-purple)]/20 text-[var(--accent-purple)]">
              👤 {npcCount} NPC{npcCount > 1 ? 'S' : ''}
            </span>
          )}
        </div>
      )}

      {/* Routes */}
      {region.routes.length > 0 && connectivity !== 'disconnected' && (
        <div className="mb-3">
          <h4 className="text-xs font-bold text-[var(--text-muted)] mb-2 tracking-wider">
            CONNECTED REGIONS
          </h4>
          <div className="space-y-1.5">
            {region.routes.slice(0, 4).map((route, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs">
                <span className="text-[var(--text-secondary)]">
                  → {route.to.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </span>
                <span className="text-[var(--text-muted)]">
                  {route.requirements.length === 0 ? 'OPEN' : 
                   route.contested ? 'CONTESTED' : 'RESTRICTED'}
                </span>
              </div>
            ))}
            {region.routes.length > 4 && (
              <span className="text-xs text-[var(--text-muted)]">
                +{region.routes.length - 4} more...
              </span>
            )}
          </div>
        </div>
      )}

      {/* Points of interest */}
      {connectivity === 'embedded' && region.pointsOfInterest.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-[var(--text-muted)] mb-2 tracking-wider">
            POINTS OF INTEREST
          </h4>
          <div className="space-y-1">
            {region.pointsOfInterest.slice(0, 3).map((poi, idx) => (
              <div key={idx} className="text-xs text-[var(--accent-steel)]">
                • {poi}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nexus presence indicator */}
      <div className="mt-3 pt-3 border-t border-[var(--border-secondary)] flex items-center justify-between">
        <span className="text-xs text-[var(--text-muted)]">NEXUS PRESENCE</span>
        <div className="flex gap-1">
          {[1, 2, 3].map((level) => (
            <div
              key={level}
              className="w-2 h-2 rounded-sm"
              style={{
                backgroundColor: level <= (region.nexusPresence === 'high' ? 3 : region.nexusPresence === 'medium' ? 2 : 1) 
                  ? 'var(--faction-nexus)' 
                  : 'var(--border-secondary)'
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default MapTooltip;
