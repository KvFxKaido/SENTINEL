import { useState, useCallback, useMemo, useEffect } from 'react';
import type { Region, RegionData, RegionConnectivity, ContentMarker } from './types';
import { MapTooltip } from './MapTooltip';
import { RegionNode } from './RegionNode';
import { ConnectionLines } from './ConnectionLines';
import { MapLegend } from './MapLegend';

/**
 * WorldMap — SENTINEL strategic world map (SVG-based).
 *
 * This is a props-driven component. All data comes from the bridge API.
 * The map never stores or mutates campaign state.
 *
 * @see architecture/Sentinel 2D.md, Section 7 (Strategic World Map)
 */

interface WorldMapProps {
  /** All region static data, keyed by region id */
  regions: Record<string, RegionData>;
  /** Current region id from campaign state */
  currentRegion: Region;
  /** Per-region connectivity from MapState */
  regionStates: Record<string, RegionConnectivity>;
  /** Per-region content markers (aggregated server-side) */
  markers: Record<string, ContentMarker[]>;
  /** Called when player clicks a region */
  onRegionClick?: (region: Region) => void;
  /** Show the legend panel */
  showLegend?: boolean;
  /** Current session number (displayed in header) */
  session?: number;
}

export function WorldMap({
  regions,
  currentRegion,
  regionStates,
  markers,
  onRegionClick,
  showLegend = true,
  session,
}: WorldMapProps) {
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

  const viewBoxWidth = 100;
  const viewBoxHeight = 90;

  // Derive connection lines from route data
  const connections = useMemo(() => {
    const conn: { from: Region; to: Region; type: 'open' | 'conditional' | 'contested' | 'risky' }[] = [];
    const seen = new Set<string>();

    Object.values(regions).forEach((region) => {
      if (!region.routes) return;
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
  }, [regions]);

  // Get current region name for header display
  const currentRegionName = regions[currentRegion]?.name || currentRegion;

  return (
    <div
      className="map-container scanlines"
      style={{ position: 'relative', width: '100%', height: '100%', minHeight: '600px' }}
      onMouseMove={handleMouseMove}
    >
      {/* Grid overlay */}
      <div className="grid-overlay" style={{ position: 'absolute', inset: 0 }} />

      {/* Nexus presence overlay */}
      <div
        className="nexus-overlay"
        style={{ position: 'absolute', inset: 0, '--x': '65%', '--y': '35%' } as React.CSSProperties}
      />

      {/* Main SVG Map */}
      <svg
        viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
        style={{ width: '100%', height: '100%' }}
        preserveAspectRatio="xMidYMid meet"
      >
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
      {hoveredRegion && regions[hoveredRegion] && (
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
      <div style={{ position: 'absolute', top: '16px', left: '16px', pointerEvents: 'none' }}>
        <div style={{
          background: 'rgba(0,0,0,0.8)',
          border: '1px solid var(--border-primary)',
          borderRadius: '4px',
          padding: '12px 16px',
          backdropFilter: 'blur(8px)',
        }}>
          <h1 className="terminal-text" style={{
            fontSize: '18px',
            fontWeight: 'bold',
            color: 'var(--accent-steel)',
            letterSpacing: '0.1em',
            margin: 0,
          }}>
            NETWORK MAP
          </h1>
          <p className="terminal-text" style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            marginTop: '4px',
            margin: 0,
          }}>
            SENTINEL TACTICAL DISPLAY // v2.1.4
          </p>
          <div className="terminal-text" style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '12px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>
              CURRENT: <span style={{ color: 'var(--accent-cyan)' }}>{currentRegionName.toUpperCase()}</span>
            </span>
            {session !== undefined && (
              <span style={{ color: 'var(--text-muted)' }}>
                SESSION: <span style={{ color: 'var(--accent-steel)' }}>{String(session).padStart(2, '0')}</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Status panel */}
      <div style={{ position: 'absolute', top: '16px', right: '16px', pointerEvents: 'none' }}>
        <div style={{
          background: 'rgba(0,0,0,0.8)',
          border: '1px solid var(--border-primary)',
          borderRadius: '4px',
          padding: '8px 12px',
          backdropFilter: 'blur(8px)',
        }}>
          <div className="terminal-text" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--accent-green)',
              display: 'inline-block',
            }} />
            <span style={{ color: 'var(--text-secondary)' }}>SYSTEM ONLINE</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WorldMap;
