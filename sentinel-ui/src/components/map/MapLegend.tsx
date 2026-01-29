import { useState } from 'react';
import { FACTION_INFO } from './types';

export function MapLegend() {
  const [isExpanded, setIsExpanded] = useState(true);

  const connectivityItems = [
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <rect x="3" y="4" width="10" height="8" rx="1.5" fill="var(--metroid-unvisited-fill)" stroke="var(--metroid-unvisited-stroke)" strokeWidth="1" />
        </svg>
      ),
      label: 'Unvisited',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <rect x="3" y="4" width="10" height="8" rx="1.5" fill="var(--metroid-visited-fill)" stroke="var(--metroid-visited-stroke)" strokeWidth="1.5" strokeDasharray="2,2" />
        </svg>
      ),
      label: 'Aware',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <rect x="3" y="4" width="10" height="8" rx="1.5" fill="var(--metroid-visited-fill)" stroke="var(--metroid-visited-stroke)" strokeWidth="2" />
        </svg>
      ),
      label: 'Connected',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <rect x="3" y="4" width="10" height="8" rx="1.5" fill="var(--metroid-embedded-fill)" stroke="var(--metroid-embedded-stroke)" strokeWidth="2" />
        </svg>
      ),
      label: 'Embedded',
    },
  ];

  const markerItems = [
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <rect x="4" y="4" width="8" height="8" rx="1.5" fill="none" stroke="var(--metroid-current)" strokeWidth="2" />
          <rect x="6" y="6" width="4" height="4" rx="1" fill="var(--metroid-current)" opacity="0.3" />
        </svg>
      ),
      label: 'Current Location',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <rect x="2" y="6" width="4" height="4" rx="0.5" fill="var(--metroid-item-marker)" />
          <text x="4" y="9" textAnchor="middle" style={{ fontSize: '6px', fill: 'black', fontWeight: 'bold' }}>J</text>
        </svg>
      ),
      label: 'Job Available',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <polygon points="8,2 11,8 8,11 5,8" fill="var(--metroid-secret-marker)" />
          <text x="8" y="8.5" textAnchor="middle" style={{ fontSize: '5px', fill: 'black', fontWeight: 'bold' }}>!</text>
        </svg>
      ),
      label: 'Dormant Thread',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="4" cy="8" r="3" fill="var(--metroid-npc-marker)" />
          <text x="4" y="9" textAnchor="middle" style={{ fontSize: '6px', fill: 'white', fontWeight: 'bold' }}>2</text>
        </svg>
      ),
      label: 'NPCs Present',
    },
  ];

  const routeItems = [
    {
      symbol: (
        <svg width="24" height="12" viewBox="0 0 24 12">
          {/* Metroid-style corridor: horizontal passage connecting rooms */}
          <rect x="2" y="4" width="4" height="4" rx="1" fill="var(--metroid-visited-fill)" stroke="var(--metroid-corridor-normal)" strokeWidth="1.5" />
          <line x1="6" y1="6" x2="18" y2="6" stroke="var(--metroid-corridor-normal)" strokeWidth="2" />
          <rect x="18" y="4" width="4" height="4" rx="1" fill="var(--metroid-visited-fill)" stroke="var(--metroid-corridor-normal)" strokeWidth="1.5" />
        </svg>
      ),
      label: 'Open Passage',
    },
    {
      symbol: (
        <svg width="24" height="12" viewBox="0 0 24 12">
          <rect x="2" y="4" width="4" height="4" rx="1" fill="var(--metroid-visited-fill)" stroke="var(--metroid-corridor-conditional)" strokeWidth="1.5" strokeDasharray="2,1" />
          <line x1="6" y1="6" x2="18" y2="6" stroke="var(--metroid-corridor-conditional)" strokeWidth="2" strokeDasharray="3,2" />
          <rect x="18" y="4" width="4" height="4" rx="1" fill="var(--metroid-visited-fill)" stroke="var(--metroid-corridor-conditional)" strokeWidth="1.5" strokeDasharray="2,1" />
        </svg>
      ),
      label: 'Conditional',
    },
    {
      symbol: (
        <svg width="24" height="12" viewBox="0 0 24 12">
          <rect x="2" y="4" width="4" height="4" rx="1" fill="rgba(245, 158, 11, 0.2)" stroke="var(--metroid-corridor-contested)" strokeWidth="2" />
          <line x1="6" y1="6" x2="18" y2="6" stroke="var(--metroid-corridor-contested)" strokeWidth="2.5" />
          <rect x="18" y="4" width="4" height="4" rx="1" fill="rgba(245, 158, 11, 0.2)" stroke="var(--metroid-corridor-contested)" strokeWidth="2" />
        </svg>
      ),
      label: 'Contested Border',
    },
    {
      symbol: (
        <svg width="24" height="12" viewBox="0 0 24 12">
          <rect x="2" y="4" width="4" height="4" rx="1" fill="var(--metroid-visited-fill)" stroke="var(--metroid-corridor-risky)" strokeWidth="1.5" />
          <line x1="6" y1="6" x2="18" y2="6" stroke="var(--metroid-corridor-risky)" strokeWidth="2" strokeDasharray="2,3" />
          <rect x="18" y="4" width="4" height="4" rx="1" fill="var(--metroid-visited-fill)" stroke="var(--metroid-corridor-risky)" strokeWidth="1.5" />
        </svg>
      ),
      label: 'Risky Route',
    },
  ];

  const factionItems = Object.values(FACTION_INFO).map(f => ({
    symbol: (
      <svg width="16" height="16" viewBox="0 0 16 16">
        {/* Room outline with faction color stripe */}
        <rect x="2" y="3" width="12" height="10" rx="1.5" fill="var(--metroid-visited-fill)" stroke="var(--metroid-visited-stroke)" strokeWidth="1.5" />
        <rect x="11" y="4" width="2" height="8" rx="0.5" fill={f.color} opacity="0.8" />
      </svg>
    ),
    label: f.shortName,
    color: f.color,
  }));

  return (
    <div
      className="map-legend"
      style={{
        position: 'absolute',
        bottom: '16px',
        left: '16px',
        background: 'rgba(0,0,0,0.9)',
        border: '1px solid var(--border-primary)',
        borderRadius: '12px',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        overflow: 'hidden',
        maxWidth: isExpanded ? '280px' : '140px',
      }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--text-secondary)',
        }}
      >
        <span className="terminal-text" style={{
          fontSize: '11px',
          fontWeight: 'bold',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
        }}>
          Map Data
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          style={{ transition: 'transform 0.2s', transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          <path d="M2 4 L6 8 L10 4" stroke="var(--text-muted)" strokeWidth="1.5" fill="none" />
        </svg>
      </button>

      {/* Top accent line */}
      <div style={{
        height: '1px',
        background: 'linear-gradient(90deg, transparent 0%, var(--accent-steel) 30%, var(--accent-cyan) 50%, var(--accent-steel) 70%, transparent 100%)',
        opacity: 0.6,
      }} />

      {isExpanded && (
        <div style={{ padding: '0 16px 16px', maxHeight: '400px', overflowY: 'auto' }}>
          {/* Connectivity States */}
          <Section title="Sectors">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {connectivityItems.map((item, idx) => (
                <LegendItem key={idx} symbol={item.symbol} label={item.label} />
              ))}
            </div>
          </Section>

          {/* Content Markers */}
          <Section title="Signals">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {markerItems.map((item, idx) => (
                <LegendItem key={idx} symbol={item.symbol} label={item.label} />
              ))}
            </div>
          </Section>

          {/* Route Types */}
          <Section title="Passages">
            {routeItems.map((item, idx) => (
              <LegendItem key={idx} symbol={item.symbol} label={item.label} />
            ))}
          </Section>

          {/* Factions */}
          <Section title="Networks">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {factionItems.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {item.symbol}
                  <span style={{ fontSize: '11px', color: item.color, fontWeight: 500 }}>{item.label}</span>
                </div>
              ))}
            </div>
          </Section>

          {/* Help text */}
          <div style={{
            paddingTop: '12px',
            borderTop: '1px solid var(--border-secondary)',
            marginTop: '8px',
          }}>
            <p style={{ fontSize: '10px', color: 'var(--text-muted)', lineHeight: '1.5', margin: 0 }}>
              Rooms show network reach. Yellow = current sector.
              Corridors link adjacent regions. Markers indicate content.
            </p>
          </div>
        </div>
      )}

      {!isExpanded && (
        <div style={{ padding: '0 16px 12px' }}>
          <p style={{ fontSize: '10px', color: 'var(--text-muted)', margin: 0 }}>
            Click to expand
          </p>
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <h4 className="terminal-text" style={{ 
        fontSize: '9px', 
        fontWeight: 'bold', 
        color: 'var(--text-muted)', 
        marginBottom: '10px', 
        letterSpacing: '0.12em', 
        textTransform: 'uppercase',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <span style={{
          width: '8px',
          height: '2px',
          background: 'var(--accent-steel)',
          borderRadius: '1px',
        }} />
        {title}
      </h4>
      {children}
    </div>
  );
}

function LegendItem({ symbol, label }: { symbol: React.ReactNode; label: string }) {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '10px',
      padding: '4px 8px',
      borderRadius: '4px',
      transition: 'background 0.15s ease',
    }}>
      {symbol}
      <span style={{ 
        fontSize: '11px', 
        color: 'var(--text-secondary)',
      }}>{label}</span>
    </div>
  );
}

export default MapLegend;
