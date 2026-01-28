import { useState, useCallback, useMemo } from 'react';
import type { Region, RegionConnectivity, ContentMarker } from '@/types/map';
import { regions } from '@/data/regions';
import { MapTooltip } from './MapTooltip';
import { RegionNode } from './RegionNode';
import { ConnectionLines } from './ConnectionLines';
import { MapLegend } from './MapLegend';

// Demo state for the map - simulating a campaign in progress
const demoRegionStates: Record<Region, RegionConnectivity> = {
  rust_corridor: 'embedded',
  breadbasket: 'connected',
  northern_reaches: 'connected',
  pacific_corridor: 'aware',
  appalachian_hollows: 'aware',
  northeast_scar: 'disconnected',
  desert_sprawl: 'disconnected',
  texas_spine: 'disconnected',
  gulf_passage: 'disconnected',
  sovereign_south: 'disconnected',
  frozen_edge: 'disconnected',
};

// Demo content markers
const demoMarkers: Record<Region, ContentMarker[]> = {
  rust_corridor: [
    { type: 'current' },
    { type: 'npc', count: 3 },
    { type: 'job' },
  ],
  breadbasket: [
    { type: 'npc', count: 2 },
    { type: 'thread' },
  ],
  northern_reaches: [
    { type: 'npc', count: 1 },
  ],
  pacific_corridor: [
    { type: 'job' },
  ],
  appalachian_hollows: [],
  northeast_scar: [],
  desert_sprawl: [],
  texas_spine: [],
  gulf_passage: [],
  sovereign_south: [],
  frozen_edge: [],
};

interface WorldMapProps {
  currentRegion?: Region;
  regionStates?: Record<Region, RegionConnectivity>;
  markers?: Record<Region, ContentMarker[]>;
  onRegionClick?: (region: Region) => void;
  showLegend?: boolean;
}

export const WorldMap = ({
  currentRegion = 'rust_corridor',
  regionStates = demoRegionStates,
  markers = demoMarkers,
  onRegionClick,
  showLegend = true,
}: WorldMapProps) => {
  const [hoveredRegion, setHoveredRegion] = useState<Region | null>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    setMousePosition({ x: e.clientX, y: e.clientY });
  }, []);

  const handleRegionHover = useCallback((region: Region | null) => {
    setHoveredRegion(region);
  }, []);

  const handleRegionClick = useCallback((region: Region) => {
    setSelectedRegion(region);
    onRegionClick?.(region);
  }, [onRegionClick]);

  // Calculate viewBox dimensions
  const viewBoxWidth = 100;
  const viewBoxHeight = 90;

  // Get all connections for rendering lines
  const connections = useMemo(() => {
    const conn: { from: Region; to: Region; type: 'open' | 'conditional' | 'contested' | 'risky' }[] = [];
    const seen = new Set<string>();

    Object.values(regions).forEach((region) => {
      region.routes.forEach((route) => {
        const key = [region.id, route.to].sort().join('-');
        if (!seen.has(key)) {
          seen.add(key);
          let type: 'open' | 'conditional' | 'contested' | 'risky' = 'open';
          if (route.contested) type = 'contested';
          else if (route.risky) type = 'risky';
          else if (route.requirements.length > 0) type = 'conditional';
          conn.push({ from: region.id, to: route.to, type });
        }
      });
    });

    return conn;
  }, []);

  return (
    <div 
      className="relative w-full h-full min-h-[600px] map-container scanlines"
      onMouseMove={handleMouseMove}
    >
      {/* Grid overlay */}
      <div className="absolute inset-0 grid-overlay" />
      
      {/* Nexus presence overlay */}
      <div 
        className="absolute inset-0 nexus-overlay"
        style={{ '--x': '65%', '--y': '35%' } as React.CSSProperties}
      />

      {/* Main SVG Map */}
      <svg
        viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Defs for filters and gradients */}
        <defs>
          {/* Glow filter for embedded regions */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          {/* Pulse filter for current location */}
          <filter id="pulse-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Gradient for region nodes */}
          <radialGradient id="node-gradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.1)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
        </defs>

        {/* Connection lines between regions */}
        <ConnectionLines 
          connections={connections}
          regions={regions}
          regionStates={regionStates}
        />

        {/* Region nodes */}
        {Object.values(regions).map((region) => (
          <RegionNode
            key={region.id}
            region={region}
            connectivity={regionStates[region.id] || 'disconnected'}
            markers={markers[region.id] || []}
            isCurrent={region.id === currentRegion}
            isSelected={region.id === selectedRegion}
            isHovered={region.id === hoveredRegion}
            onHover={handleRegionHover}
            onClick={handleRegionClick}
          />
        ))}
      </svg>

      {/* Tooltip */}
      {hoveredRegion && (
        <MapTooltip
          region={regions[hoveredRegion]}
          connectivity={regionStates[hoveredRegion] || 'disconnected'}
          markers={markers[hoveredRegion] || []}
          mousePosition={mousePosition}
        />
      )}

      {/* Legend */}
      {showLegend && <MapLegend />}

      {/* Header info */}
      <div className="absolute top-4 left-4 pointer-events-none">
        <div className="bg-black/80 border border-[var(--border-primary)] rounded px-4 py-3 backdrop-blur-sm">
          <h1 className="text-lg font-bold text-[var(--accent-steel)] terminal-text tracking-wider">
            NETWORK MAP
          </h1>
          <p className="text-xs text-[var(--text-muted)] terminal-text mt-1">
            SENTINEL TACTICAL DISPLAY // v2.1.4
          </p>
          <div className="flex items-center gap-4 mt-2 text-xs terminal-text">
            <span className="text-[var(--text-secondary)]">
              CURRENT: <span className="text-[var(--accent-cyan)]">{regions[currentRegion].name.toUpperCase()}</span>
            </span>
            <span className="text-[var(--text-muted)]">
              SESSION: <span className="text-[var(--accent-steel)]">05</span>
            </span>
          </div>
        </div>
      </div>

      {/* Status panel */}
      <div className="absolute top-4 right-4 pointer-events-none">
        <div className="bg-black/80 border border-[var(--border-primary)] rounded px-3 py-2 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-xs terminal-text">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-green)] animate-pulse" />
            <span className="text-[var(--text-secondary)]">SYSTEM ONLINE</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorldMap;
