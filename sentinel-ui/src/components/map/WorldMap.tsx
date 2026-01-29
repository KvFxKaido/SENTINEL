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
      {/* Grid overlay - Metroid-style navigation grid */}
      <div className="grid-overlay" style={{ position: 'absolute', inset: 0 }} />
      <div className="grid-overlay-unvisited" style={{ position: 'absolute', inset: 0 }} />

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

      {/* Header info - Metroid-style map terminal */}
      <div style={{ position: 'absolute', top: '16px', left: '16px', pointerEvents: 'none' }}>
        <div className="map-header" style={{
          background: 'var(--bg-panel-glass)',
          border: '1px solid var(--border-primary)',
          borderRadius: '8px',
          padding: '14px 18px',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        }}>
          {/* Top accent line - Metroid energy bar style */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: '0',
            right: '0',
            height: '2px',
            background: 'linear-gradient(90deg, var(--metroid-current) 0%, var(--accent-cyan) 50%, var(--metroid-current) 100%)',
            opacity: 0.8,
            borderRadius: '8px 8px 0 0',
          }} />
          <h1 className="terminal-text" style={{
            fontSize: '18px',
            fontWeight: 'bold',
            color: 'var(--metroid-visited-stroke)',
            letterSpacing: '0.15em',
            margin: 0,
            textTransform: 'uppercase',
          }}>
            SECTOR MAP
          </h1>
          <p className="terminal-text" style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            margin: '4px 0 0',
            letterSpacing: '0.08em',
          }}>
            NAVIGATION SYSTEM v2.2 // GRID ACTIVE
          </p>
          <div className="terminal-text" style={{ display: 'flex', gap: '20px', marginTop: '10px', fontSize: '11px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>
              LOC: <span style={{ color: 'var(--metroid-current)', fontWeight: 'bold' }}>{currentRegionName.toUpperCase()}</span>
            </span>
            {session !== undefined && (
              <span style={{ color: 'var(--text-muted)' }}>
                SEQ: <span style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>{String(session).padStart(2, '0')}</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Status panel - Metroid-style system indicator */}
      <div style={{ position: 'absolute', top: '16px', right: '380px', pointerEvents: 'none' }}>
        <div style={{
          background: 'var(--bg-panel-glass)',
          border: '1px solid var(--border-primary)',
          borderRadius: '6px',
          padding: '8px 14px',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        }}>
          <div className="terminal-text" style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '10px' }}>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '1px',
              backgroundColor: 'var(--metroid-item-marker)',
              display: 'inline-block',
              boxShadow: '0 0 6px var(--metroid-item-marker)',
              animation: 'pulse-glow 2s ease-in-out infinite',
            }} />
            <span style={{ color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Map Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WorldMap;
