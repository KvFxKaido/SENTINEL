import type { Region, RegionData, RegionConnectivity } from './types';

interface Connection {
  from: Region;
  to: Region;
  type: 'open' | 'conditional' | 'contested' | 'risky';
}

interface ConnectionLinesProps {
  connections: Connection[];
  regions: Record<string, RegionData>;
  regionStates: Record<string, RegionConnectivity>;
}

// Metroid-style corridor colors
const getCorridorStyle = (type: Connection['type']) => {
  switch (type) {
    case 'open':
      return {
        stroke: 'var(--metroid-corridor-normal)',
        strokeWidth: 2,
        strokeDasharray: 'none',
        opacity: 0.8,
      };
    case 'conditional':
      return {
        stroke: 'var(--metroid-corridor-conditional)',
        strokeWidth: 2,
        strokeDasharray: '2,2',
        opacity: 0.6,
      };
    case 'contested':
      return {
        stroke: 'var(--metroid-corridor-contested)',
        strokeWidth: 2.5,
        strokeDasharray: 'none',
        opacity: 0.9,
      };
    case 'risky':
      return {
        stroke: 'var(--metroid-corridor-risky)',
        strokeWidth: 2,
        strokeDasharray: '1,3',
        opacity: 0.6,
      };
    default:
      return {
        stroke: 'var(--metroid-corridor-normal)',
        strokeWidth: 1.5,
        strokeDasharray: 'none',
        opacity: 0.5,
      };
  }
};

// Calculate Manhattan (orthogonal) path between two points
// Uses a simple L-shaped path with a corner
const calculateManhattanPath = (
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  roomWidth: number = 10,
  roomHeight: number = 8
): string => {
  // Offset from room center to edge
  const offsetX = roomWidth / 2 + 1;
  const offsetY = roomHeight / 2 + 1;

  // Determine which direction to exit/enter rooms
  const dx = x2 - x1;
  const dy = y2 - y1;

  // Start point (exit from first room)
  let startX = x1;
  let startY = y1;

  // End point (enter second room)
  let endX = x2;
  let endY = y2;

  // Adjust start/end to be at room edges
  if (Math.abs(dx) > Math.abs(dy)) {
    // Horizontal dominant - exit/enter horizontally
    startX = dx > 0 ? x1 + offsetX : x1 - offsetX;
    endX = dx > 0 ? x2 - offsetX : x2 + offsetX;
  } else {
    // Vertical dominant - exit/enter vertically
    startY = dy > 0 ? y1 + offsetY : y1 - offsetY;
    endY = dy > 0 ? y2 - offsetY : y2 + offsetY;
  }

  // Calculate the corner point for L-shaped path
  // Use midpoint approach for cleaner looking corridors
  let cornerX: number;
  let cornerY: number;

  if (Math.abs(dx) > Math.abs(dy)) {
    // Horizontal first, then vertical
    cornerX = (startX + endX) / 2;
    cornerY = startY;
    // Second segment goes from corner to end (vertical)
    const secondCornerX = cornerX;
    const secondCornerY = endY;

    return `M ${startX} ${startY} L ${cornerX} ${cornerY} L ${secondCornerX} ${secondCornerY} L ${endX} ${endY}`;
  } else {
    // Vertical first, then horizontal
    cornerX = startX;
    cornerY = (startY + endY) / 2;
    // Second segment goes from corner to end (horizontal)
    const secondCornerX = endX;
    const secondCornerY = cornerY;

    return `M ${startX} ${startY} L ${cornerX} ${cornerY} L ${secondCornerX} ${secondCornerY} L ${endX} ${endY}`;
  }
};

// Simple direct path for very close rooms or fallback
const calculateDirectPath = (
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  roomWidth: number = 10,
  roomHeight: number = 8
): string => {
  const offsetX = roomWidth / 2;
  const offsetY = roomHeight / 2;

  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.sqrt(dx * dx + dy * dy);

  // Calculate unit vector
  const ux = dx / dist;
  const uy = dy / dist;

  // Start and end points at room edges
  const startX = x1 + ux * offsetX;
  const startY = y1 + uy * offsetY;
  const endX = x2 - ux * offsetX;
  const endY = y2 - uy * offsetY;

  return `M ${startX} ${startY} L ${endX} ${endY}`;
};

export function ConnectionLines({
  connections,
  regions,
  regionStates,
}: ConnectionLinesProps) {
  const isConnectionVisible = (from: Region, to: Region): boolean => {
    const fromState = regionStates[from] || 'disconnected';
    const toState = regionStates[to] || 'disconnected';
    return fromState !== 'disconnected' || toState !== 'disconnected';
  };

  return (
    <g>
      {connections.map((conn, index) => {
        const fromRegion = regions[conn.from];
        const toRegion = regions[conn.to];

        if (!fromRegion || !toRegion) return null;
        if (!isConnectionVisible(conn.from, conn.to)) return null;

        const { x: x1, y: y1 } = fromRegion.position;
        const { x: x2, y: y2 } = toRegion.position;
        const style = getCorridorStyle(conn.type);

        const fromState = regionStates[conn.from] || 'disconnected';
        const toState = regionStates[conn.to] || 'disconnected';
        const maxConnectivity = Math.max(
          fromState === 'embedded' ? 3 :
          fromState === 'connected' ? 2 :
          fromState === 'aware' ? 1 : 0,
          toState === 'embedded' ? 3 :
          toState === 'connected' ? 2 :
          toState === 'aware' ? 1 : 0,
        );
        const opacityMultiplier = maxConnectivity >= 2 ? 1 : maxConnectivity === 1 ? 0.6 : 0.3;

        // Calculate distance to decide path style
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Use direct path for very close rooms, Manhattan for others
        const pathD = dist < 15
          ? calculateDirectPath(x1, y1, x2, y2)
          : calculateManhattanPath(x1, y1, x2, y2);

        return (
          <path
            key={`${conn.from}-${conn.to}-${index}`}
            d={pathD}
            fill="none"
            stroke={style.stroke}
            strokeWidth={style.strokeWidth}
            strokeDasharray={style.strokeDasharray}
            opacity={style.opacity * opacityMultiplier}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="connection-corridor"
            style={{ transition: 'all 0.3s ease' }}
          />
        );
      })}
    </g>
  );
}

export default ConnectionLines;
