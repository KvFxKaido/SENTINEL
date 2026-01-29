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
        fill: 'var(--metroid-unvisited-fill)',
        stroke: 'var(--metroid-unvisited-stroke)',
        strokeWidth: 1,
        strokeDasharray: 'none',
        opacity: 0.6,
      };
    case 'aware':
      return {
        fill: 'var(--metroid-visited-fill)',
        stroke: 'var(--metroid-visited-stroke)',
        strokeWidth: 1.5,
        strokeDasharray: '3,2',
        opacity: 0.8,
      };
    case 'connected':
      return {
        fill: 'var(--metroid-visited-fill)',
        stroke: 'var(--metroid-visited-stroke)',
        strokeWidth: 2,
        strokeDasharray: 'none',
        opacity: 1,
      };
    case 'embedded':
      return {
        fill: 'var(--metroid-embedded-fill)',
        stroke: 'var(--metroid-embedded-stroke)',
        strokeWidth: 2,
        strokeDasharray: 'none',
        opacity: 1,
      };
    default:
      return {
        fill: 'var(--metroid-unvisited-fill)',
        stroke: 'var(--metroid-unvisited-stroke)',
        strokeWidth: 1,
        strokeDasharray: 'none',
        opacity: 0.6,
      };
  }
};

// Metroid-style room sizes based on importance/connectivity
const getRoomSize = (connectivity: RegionConnectivity, isCurrent: boolean, isHovered: boolean) => {
  const baseScale = connectivity === 'embedded' ? 1.3 : connectivity === 'connected' ? 1.1 : 1;
  const currentScale = isCurrent ? 1.2 : 1;
  const hoverScale = isHovered ? 1.15 : 1;
  return baseScale * currentScale * hoverScale;
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

  const scale = getRoomSize(connectivity, isCurrent, isHovered);
  const baseWidth = 10;
  const baseHeight = 8;
  const width = baseWidth * scale;
  const height = baseHeight * scale;

  const showName = connectivity !== 'disconnected' || isHovered;

  const npcCount = markers.filter(m => m.type === 'npc').reduce((sum, m) => sum + (m.count || 1), 0);
  const hasJob = markers.some(m => m.type === 'job');
  const hasThread = markers.some(m => m.type === 'thread');

  // Room corner radius - sharper for Metroid aesthetic
  const cornerRadius = 1.5;

  return (
    <g
      className="region-node"
      onMouseEnter={() => onHover(region.id)}
      onMouseLeave={() => onHover(null)}
      onClick={() => onClick(region.id)}
      style={{ cursor: 'pointer' }}
    >
      {/* Selection ring - outer glow for Metroid style */}
      {isSelected && (
        <rect
          x={x - width / 2 - 2}
          y={y - height / 2 - 2}
          width={width + 4}
          height={height + 4}
          rx={cornerRadius + 1}
          fill="none"
          stroke="var(--metroid-current)"
          strokeWidth={2}
          strokeOpacity={0.8}
          className="selection-ring"
        />
      )}

      {/* Main room rectangle - Metroid style */}
      <rect
        x={x - width / 2}
        y={y - height / 2}
        width={width}
        height={height}
        rx={cornerRadius}
        fill={connStyle.fill}
        stroke={isCurrent ? 'var(--metroid-current)' : connStyle.stroke}
        strokeWidth={isCurrent ? 3 : connStyle.strokeWidth}
        strokeDasharray={connStyle.strokeDasharray as string}
        opacity={connStyle.opacity}
        filter={connectivity === 'embedded' || isCurrent ? 'url(#glow)' : undefined}
        style={{ transition: 'all 0.2s ease' }}
        className={isCurrent ? 'metroid-current-room' : ''}
      />

      {/* Inner detail - faction stripe on the right side */}
      <rect
        x={x + width / 2 - 2}
        y={y - height / 2 + 1}
        width={1.5}
        height={height - 2}
        rx={0.5}
        fill={factionColor}
        opacity={connectivity === 'disconnected' ? 0.2 : 0.8}
      />

      {/* Current location indicator - Metroid energy tank style */}
      {isCurrent && (
        <>
          {/* Outer pulse ring */}
          <rect
            x={x - width / 2 - 4}
            y={y - height / 2 - 4}
            width={width + 8}
            height={height + 8}
            rx={cornerRadius + 2}
            fill="none"
            stroke="var(--metroid-current)"
            strokeWidth={1}
            strokeOpacity={0.4}
            className="pulse-current"
          />
          {/* Inner glow */}
          <rect
            x={x - width / 2 + 1}
            y={y - height / 2 + 1}
            width={width - 2}
            height={height - 2}
            rx={cornerRadius - 0.5}
            fill="var(--metroid-current)"
            fillOpacity={0.15}
            className="pulse-current"
          />
        </>
      )}

      {/* Region name label - positioned below room */}
      {showName && (
        <text
          x={x}
          y={y + height / 2 + 8}
          textAnchor="middle"
          className="terminal-text"
          style={{
            fontSize: connectivity === 'embedded' ? '3px' : '2.5px',
            fontWeight: connectivity === 'embedded' ? 'bold' : 'normal',
            fill: isCurrent ? 'var(--metroid-current)' : (connectivity === 'disconnected' ? 'var(--metroid-unvisited-stroke)' : 'var(--metroid-visited-stroke)'),
            opacity: connectivity === 'aware' ? 0.8 : 1,
            pointerEvents: 'none',
            userSelect: 'none',
          }}
        >
          {region.name.toUpperCase()}
        </text>
      )}

      {/* Disconnected indicator - subtle corner markers */}
      {connectivity === 'disconnected' && !isHovered && (
        <>
          <line x1={x - 2} y1={y - 2} x2={x - 1} y2={y - 1} stroke="var(--metroid-unvisited-stroke)" strokeWidth={0.5} opacity={0.4} />
          <line x1={x + 2} y1={y - 2} x2={x + 1} y2={y - 1} stroke="var(--metroid-unvisited-stroke)" strokeWidth={0.5} opacity={0.4} />
          <line x1={x - 2} y1={y + 2} x2={x - 1} y2={y + 1} stroke="var(--metroid-unvisited-stroke)" strokeWidth={0.5} opacity={0.4} />
          <line x1={x + 2} y1={y + 2} x2={x + 1} y2={y + 1} stroke="var(--metroid-unvisited-stroke)" strokeWidth={0.5} opacity={0.4} />
        </>
      )}

      {/* Content markers - positioned at corners of the room */}
      {connectivity !== 'disconnected' && (
        <g>
          {/* Job marker - top left */}
          {hasJob && (
            <g transform={`translate(${x - width / 2 - 1}, ${y - height / 2 - 1})`}>
              <rect x={-1.5} y={-1.5} width={3} height={3} rx={0.5} fill="var(--metroid-item-marker)" />
              <text y={0.8} textAnchor="middle" style={{ fontSize: '2px', fill: 'black', fontWeight: 'bold' }}>J</text>
            </g>
          )}

          {/* Thread marker - top right */}
          {hasThread && (
            <g transform={`translate(${x + width / 2 + 1}, ${y - height / 2 - 1})`}>
              <polygon
                points="0,-2 1.8,0.5 0,3 -1.8,0.5"
                fill="var(--metroid-secret-marker)"
              />
              <text y={1.2} textAnchor="middle" style={{ fontSize: '1.8px', fill: 'black', fontWeight: 'bold' }}>!</text>
            </g>
          )}

          {/* NPC count - bottom left */}
          {npcCount > 0 && (
            <g transform={`translate(${x - width / 2 - 1}, ${y + height / 2 + 1})`}>
              <circle r={2} fill="var(--metroid-npc-marker)" />
              <text y={0.8} textAnchor="middle" style={{ fontSize: '1.8px', fill: 'white', fontWeight: 'bold' }}>
                {npcCount}
              </text>
            </g>
          )}
        </g>
      )}

      {/* Hover highlight - Metroid scanner style */}
      {isHovered && (
        <rect
          x={x - width / 2 - 1}
          y={y - height / 2 - 1}
          width={width + 2}
          height={height + 2}
          rx={cornerRadius + 0.5}
          fill="none"
          stroke="var(--accent-steel)"
          strokeWidth={1}
          strokeOpacity={0.6}
        />
      )}
    </g>
  );
}

export default RegionNode;
