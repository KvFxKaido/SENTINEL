import type { Region, RegionData, RegionConnectivity } from '@/types/map';

interface Connection {
  from: Region;
  to: Region;
  type: 'open' | 'conditional' | 'contested' | 'risky';
}

interface ConnectionLinesProps {
  connections: Connection[];
  regions: Record<Region, RegionData>;
  regionStates: Record<Region, RegionConnectivity>;
}

export const ConnectionLines = ({
  connections,
  regions,
  regionStates,
}: ConnectionLinesProps) => {
  // Check if a connection should be visible based on connectivity
  const isConnectionVisible = (from: Region, to: Region): boolean => {
    const fromState = regionStates[from] || 'disconnected';
    const toState = regionStates[to] || 'disconnected';
    
    // Show if either region is at least AWARE
    return fromState !== 'disconnected' || 
           toState !== 'disconnected';
  };

  // Get line style based on connection type
  const getLineStyle = (type: Connection['type']) => {
    switch (type) {
      case 'open':
        return {
          stroke: 'var(--border-primary)',
          strokeWidth: 1.5,
          strokeDasharray: 'none',
          opacity: 0.6,
        };
      case 'conditional':
        return {
          stroke: 'var(--text-muted)',
          strokeWidth: 1.5,
          strokeDasharray: '3,3',
          opacity: 0.5,
        };
      case 'contested':
        return {
          stroke: 'var(--accent-amber)',
          strokeWidth: 2,
          strokeDasharray: 'none',
          opacity: 0.7,
        };
      case 'risky':
        return {
          stroke: 'var(--accent-red)',
          strokeWidth: 1.5,
          strokeDasharray: '2,4',
          opacity: 0.5,
        };
      default:
        return {
          stroke: 'var(--border-primary)',
          strokeWidth: 1,
          strokeDasharray: 'none',
          opacity: 0.4,
        };
    }
  };

  return (
    <g>
      {connections.map((conn, index) => {
        const fromRegion = regions[conn.from];
        const toRegion = regions[conn.to];
        
        if (!fromRegion || !toRegion) return null;
        
        // Skip if neither region is visible
        if (!isConnectionVisible(conn.from, conn.to)) return null;
        
        const { x: x1, y: y1 } = fromRegion.position;
        const { x: x2, y: y2 } = toRegion.position;
        
        const style = getLineStyle(conn.type);
        
        // Calculate opacity based on connectivity of both regions
        const fromState = regionStates[conn.from] || 'disconnected';
        const toState = regionStates[conn.to] || 'disconnected';
        const maxConnectivity = Math.max(
          fromState === 'embedded' ? 3 : 
          fromState === 'connected' ? 2 : 
          fromState === 'aware' ? 1 : 0,
          toState === 'embedded' ? 3 : 
          toState === 'connected' ? 2 : 
          toState === 'aware' ? 1 : 0
        );
        const opacityMultiplier = maxConnectivity >= 2 ? 1 : maxConnectivity === 1 ? 0.6 : 0.3;
        
        return (
          <line
            key={`${conn.from}-${conn.to}-${index}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={style.stroke}
            strokeWidth={style.strokeWidth}
            strokeDasharray={style.strokeDasharray}
            opacity={style.opacity * opacityMultiplier}
            className="connection-line"
            style={{ transition: 'all 0.3s ease' }}
          />
        );
      })}
    </g>
  );
};

export default ConnectionLines;
