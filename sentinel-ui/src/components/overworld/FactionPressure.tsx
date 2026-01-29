/**
 * FactionPressure — Visualizes faction influence in the overworld
 * 
 * Shows faction control zones, contested areas, and influence indicators.
 * This is a non-authoritative visual layer — it doesn't affect gameplay.
 */

import { useMemo } from 'react';
import type { 
  FactionPressure as FactionPressureType, 
  FactionZone,
  FactionInfluence 
} from './expansion-types';
import { FACTION_COLORS, INFLUENCE_OPACITY } from './expansion-types';

interface FactionPressureProps {
  pressure: FactionPressureType;
  canvasWidth: number;
  canvasHeight: number;
}

// ============================================================================
// Faction Pressure Overlay (Canvas-based)
// ============================================================================

export function drawFactionPressure(
  ctx: CanvasRenderingContext2D,
  pressure: FactionPressureType,
  width: number,
  height: number
) {
  // Draw faction zones
  for (const zone of pressure.zones) {
    const color = FACTION_COLORS[zone.faction] || '#8b949e';
    const opacity = INFLUENCE_OPACITY[zone.influence];
    
    if (opacity > 0) {
      ctx.fillStyle = hexToRgba(color, opacity);
      ctx.fillRect(zone.bounds.x, zone.bounds.y, zone.bounds.width, zone.bounds.height);
      
      // Zone border
      ctx.strokeStyle = hexToRgba(color, opacity * 2);
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(zone.bounds.x, zone.bounds.y, zone.bounds.width, zone.bounds.height);
      ctx.setLineDash([]);
    }
  }

  // Draw contested area indicators
  if (pressure.contestedBy.length > 0) {
    drawContestedIndicators(ctx, pressure, width, height);
  }
}

function drawContestedIndicators(
  ctx: CanvasRenderingContext2D,
  pressure: FactionPressureType,
  width: number,
  height: number
) {
  const primaryColor = FACTION_COLORS[pressure.primaryFaction] || '#8b949e';
  
  for (const contested of pressure.contestedBy) {
    const contestedColor = FACTION_COLORS[contested.faction] || '#8b949e';
    
    // Draw diagonal stripes in contested areas
    ctx.save();
    ctx.globalAlpha = 0.1;
    
    const stripeWidth = 20;
    for (let i = -height; i < width + height; i += stripeWidth * 2) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i + height, height);
      ctx.strokeStyle = contestedColor;
      ctx.lineWidth = stripeWidth / 2;
      ctx.stroke();
    }
    
    ctx.restore();
  }
}

// ============================================================================
// Faction Legend Component
// ============================================================================

interface FactionLegendProps {
  pressure: FactionPressureType;
  factionStandings?: Array<{ id: string; name: string; standing: string }>;
}

export function FactionLegend({ pressure, factionStandings }: FactionLegendProps) {
  const factions = useMemo(() => {
    const result = [
      { 
        id: pressure.primaryFaction, 
        name: pressure.primaryFaction.replace(/_/g, ' '),
        influence: pressure.primaryInfluence,
        isPrimary: true,
      },
    ];
    
    for (const contested of pressure.contestedBy) {
      result.push({
        id: contested.faction,
        name: contested.faction.replace(/_/g, ' '),
        influence: contested.influence,
        isPrimary: false,
      });
    }
    
    return result;
  }, [pressure]);

  return (
    <div className="faction-legend">
      <div className="faction-legend-title">FACTION PRESENCE</div>
      <div className="faction-legend-list">
        {factions.map(faction => {
          const color = FACTION_COLORS[faction.id] || '#8b949e';
          const standing = factionStandings?.find(f => f.id === faction.id);
          
          return (
            <div key={faction.id} className="faction-legend-item">
              <div 
                className="faction-color-dot" 
                style={{ backgroundColor: color }}
              />
              <div className="faction-info">
                <span className="faction-name">
                  {faction.name}
                  {faction.isPrimary && <span className="primary-badge">PRIMARY</span>}
                </span>
                <span className="faction-influence">{faction.influence}</span>
                {standing && (
                  <span className={`faction-standing standing-${standing.standing}`}>
                    {standing.standing}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Faction Pressure Indicator (HUD element)
// ============================================================================

interface FactionIndicatorProps {
  faction: string;
  influence: FactionInfluence;
  standing?: string;
}

export function FactionIndicator({ faction, influence, standing }: FactionIndicatorProps) {
  const color = FACTION_COLORS[faction] || '#8b949e';
  
  return (
    <div className="faction-indicator">
      <div 
        className="faction-indicator-bar"
        style={{ 
          backgroundColor: color,
          opacity: INFLUENCE_OPACITY[influence] * 4,
        }}
      />
      <span className="faction-indicator-name">{faction.replace(/_/g, ' ')}</span>
      {standing && (
        <span className={`faction-indicator-standing standing-${standing}`}>
          {standing}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// Generate Faction Zones
// ============================================================================

export function generateFactionZones(
  primaryFaction: string,
  contestedBy: string[],
  width: number,
  height: number
): FactionPressureType {
  const zones: FactionZone[] = [];
  
  // Primary faction covers most of the area
  zones.push({
    id: `${primaryFaction}-main`,
    faction: primaryFaction,
    influence: 'dominant',
    bounds: { x: 0, y: 0, width, height },
    color: FACTION_COLORS[primaryFaction] || '#8b949e',
  });

  // Contested factions have smaller zones at edges
  const edgePositions = [
    { x: 0, y: 0, width: width * 0.3, height: height * 0.4 },
    { x: width * 0.7, y: 0, width: width * 0.3, height: height * 0.4 },
    { x: 0, y: height * 0.6, width: width * 0.4, height: height * 0.4 },
    { x: width * 0.6, y: height * 0.6, width: width * 0.4, height: height * 0.4 },
  ];

  contestedBy.forEach((faction, index) => {
    if (index < edgePositions.length) {
      const pos = edgePositions[index];
      zones.push({
        id: `${faction}-contested`,
        faction,
        influence: 'contested',
        bounds: pos,
        color: FACTION_COLORS[faction] || '#8b949e',
      });
    }
  });

  return {
    primaryFaction,
    primaryInfluence: 'dominant',
    contestedBy: contestedBy.map(faction => ({
      faction,
      influence: 'contested' as FactionInfluence,
    })),
    zones,
  };
}

// ============================================================================
// Helpers
// ============================================================================

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
