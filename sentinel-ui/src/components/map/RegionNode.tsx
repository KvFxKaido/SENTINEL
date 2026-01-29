import type { Region, RegionData, RegionConnectivity, ContentMarker, Faction } from './types';
import { FACTION_COLORS } from './types';

interface RegionNodeProps {
  region: RegionData;
  connectivity: RegionConnectivity;
  markers: ContentMarker[];
  isCurrent: boolean;
  isSelected: boolean;
  isHovered: boolean;
  onHover: (region: Region | null) => void;
  onClick: (region: Region) => void;
}

const getConnectivityStyle = (connectivity: RegionConnectivity) => {
  switch (connectivity) {
    case 'disconnected':
      return {
        fill: 'var(--state-disconnected)',
        stroke: 'var(--border-secondary)',
        strokeWidth: 1,
        strokeDasharray: 'none',
        opacity: 0.5,
      };
    case 'aware':
      return {
        fill: 'transparent',
        stroke: 'var(--state-aware)',
        strokeWidth: 2,
        strokeDasharray: '4,4',
        opacity: 0.7,
      };
    case 'connected':
      return {
        fill: 'transparent',
        stroke: 'var(--state-connected)',
        strokeWidth: 2,
        strokeDasharray: 'none',
        opacity: 1,
      };
    case 'embedded':
      return {
        fill: 'var(--state-embedded)',
        stroke: 'var(--state-embedded)',
        strokeWidth: 2,
        strokeDasharray: 'none',
        opacity: 0.3,
      };
    default:
      return {
        fill: 'var(--state-disconnected)',
        stroke: 'var(--border-secondary)',
        strokeWidth: 1,
        strokeDasharray: 'none',
        opacity: 0.5,
      };
  }
};

export function RegionNode({
  region,
  connectivity,
  markers,
  isCurrent,
  isSelected,
  isHovered,
  onHover,
  onClick,
}: RegionNodeProps) {
  const { x, y } = region.position;
  const factionColor = FACTION_COLORS[region.primary_faction] || '#6b7280';
  const connStyle = getConnectivityStyle(connectivity);

  const baseRadius = connectivity === 'embedded' ? 5 : 4;
  const hoverRadius = baseRadius + 1;
  const radius = isHovered ? hoverRadius : baseRadius;

  const showName = connectivity !== 'disconnected' || isHovered;

  const npcCount = markers.filter(m => m.type === 'npc').reduce((sum, m) => sum + (m.count || 1), 0);
  const hasJob = markers.some(m => m.type === 'job');
  const hasThread = markers.some(m => m.type === 'thread');

  return (
    <g
      className="region-node"
      onMouseEnter={() => onHover(region.id)}
      onMouseLeave={() => onHover(null)}
      onClick={() => onClick(region.id)}
      style={{ cursor: 'pointer' }}
    >
      {/* Selection ring */}
      {isSelected && (
        <circle
          cx={x}
          cy={y}
          r={radius + 4}
          fill="none"
          stroke="var(--accent-cyan)"
          strokeWidth={2}
          strokeOpacity={0.6}
          className="selection-ring"
        />
      )}

      {/* Main node circle */}
      <circle
        cx={x}
        cy={y}
        r={radius}
        fill={connStyle.fill}
        stroke={isCurrent ? 'var(--accent-cyan)' : factionColor}
        strokeWidth={isCurrent ? 3 : connStyle.strokeWidth}
        strokeDasharray={connStyle.strokeDasharray as string}
        opacity={connStyle.opacity}
        filter={connectivity === 'embedded' ? 'url(#glow)' : undefined}
        style={{ transition: 'all 0.2s ease' }}
      />

      {/* Faction indicator dot */}
      <circle
        cx={x}
        cy={y}
        r={2}
        fill={factionColor}
        opacity={connectivity === 'disconnected' ? 0.3 : 1}
      />

      {/* Current location indicator */}
      {isCurrent && (
        <>
          <circle
            cx={x}
            cy={y}
            r={radius + 6}
            fill="none"
            stroke="var(--accent-cyan)"
            strokeWidth={1}
            strokeOpacity={0.4}
            className="pulse-current"
          />
          <circle
            cx={x}
            cy={y}
            r={radius + 2}
            fill="var(--accent-cyan)"
            fillOpacity={0.2}
            className="pulse-current"
          />
        </>
      )}

      {/* Region name label */}
      {showName && (
        <text
          x={x}
          y={y + radius + 10}
          textAnchor="middle"
          className="terminal-text"
          style={{
            fontSize: connectivity === 'embedded' ? '3.5px' : '3px',
            fontWeight: connectivity === 'embedded' ? 'bold' : 'normal',
            fill: connectivity === 'disconnected' ? 'var(--text-muted)' : 'var(--text-primary)',
            opacity: connectivity === 'aware' ? 0.7 : 1,
            pointerEvents: 'none',
            userSelect: 'none',
          }}
        >
          {region.name.toUpperCase()}
        </text>
      )}

      {/* Disconnected indicator */}
      {connectivity === 'disconnected' && !isHovered && (
        <text
          x={x}
          y={y + 1}
          textAnchor="middle"
          className="terminal-text"
          style={{
            fontSize: '3px',
            fill: 'var(--text-muted)',
            opacity: 0.5,
            pointerEvents: 'none',
            userSelect: 'none',
          }}
        >
          ???
        </text>
      )}

      {/* Content markers */}
      {connectivity !== 'disconnected' && (
        <g transform={`translate(${x + radius + 3}, ${y - radius - 3})`}>
          {hasJob && (
            <g>
              <circle r={2} fill="var(--accent-green)" />
              <text y={0.8} textAnchor="middle" style={{ fontSize: '2px', fill: 'black', fontWeight: 'bold' }}>J</text>
            </g>
          )}

          {hasThread && (
            <g transform={`translate(${hasJob ? 5 : 0}, 0)`}>
              <polygon
                points="0,-2 1.8,1 -1.8,1"
                fill="var(--accent-amber)"
              />
              <text y={1} textAnchor="middle" style={{ fontSize: '2px', fill: 'black', fontWeight: 'bold' }}>!</text>
            </g>
          )}

          {npcCount > 0 && (
            <g transform={`translate(0, ${hasJob || hasThread ? 5 : 0})`}>
              <circle r={2.5} fill="var(--accent-purple)" />
              <text y={1} textAnchor="middle" style={{ fontSize: '2px', fill: 'white', fontWeight: 'bold' }}>
                {npcCount}
              </text>
            </g>
          )}
        </g>
      )}

      {/* Hover highlight */}
      {isHovered && (
        <circle
          cx={x}
          cy={y}
          r={radius + 3}
          fill="none"
          stroke="var(--accent-steel)"
          strokeWidth={1}
          strokeOpacity={0.5}
        />
      )}
    </g>
  );
}

export default RegionNode;
