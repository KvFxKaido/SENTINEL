import { useState } from 'react';
import { FACTION_INFO } from './types';

export function MapLegend() {
  const [isExpanded, setIsExpanded] = useState(true);

  const connectivityItems = [
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="5" fill="var(--state-disconnected)" stroke="var(--border-secondary)" strokeWidth="1" />
        </svg>
      ),
      label: 'Disconnected',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="5" fill="none" stroke="var(--state-aware)" strokeWidth="2" strokeDasharray="3,3" />
        </svg>
      ),
      label: 'Aware',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="5" fill="none" stroke="var(--state-connected)" strokeWidth="2" />
        </svg>
      ),
      label: 'Connected',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="5" fill="var(--state-embedded)" stroke="var(--state-embedded)" strokeWidth="2" />
        </svg>
      ),
      label: 'Embedded',
    },
  ];

  const markerItems = [
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="4" fill="var(--accent-cyan)" />
          <circle cx="8" cy="8" r="6" fill="none" stroke="var(--accent-cyan)" strokeWidth="1" opacity="0.5" />
        </svg>
      ),
      label: 'Current Location',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="4" fill="var(--accent-green)" />
          <text x="8" y="10" textAnchor="middle" style={{ fontSize: '8px', fill: 'black', fontWeight: 'bold' }}>J</text>
        </svg>
      ),
      label: 'Job Available',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <polygon points="8,3 12,11 4,11" fill="var(--accent-amber)" />
          <text x="8" y="10" textAnchor="middle" style={{ fontSize: '8px', fill: 'black', fontWeight: 'bold' }}>!</text>
        </svg>
      ),
      label: 'Dormant Thread',
    },
    {
      symbol: (
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="5" fill="var(--accent-purple)" />
          <text x="8" y="10" textAnchor="middle" style={{ fontSize: '8px', fill: 'white', fontWeight: 'bold' }}>2</text>
        </svg>
      ),
      label: 'NPCs Present',
    },
  ];

  const routeItems = [
    {
      symbol: (
        <svg width="24" height="8" viewBox="0 0 24 8">
          <line x1="2" y1="4" x2="22" y2="4" stroke="var(--border-primary)" strokeWidth="2" />
        </svg>
      ),
      label: 'Open Passage',
    },
    {
      symbol: (
        <svg width="24" height="8" viewBox="0 0 24 8">
          <line x1="2" y1="4" x2="22" y2="4" stroke="var(--text-muted)" strokeWidth="2" strokeDasharray="4,3" />
        </svg>
      ),
      label: 'Conditional',
    },
    {
      symbol: (
        <svg width="24" height="8" viewBox="0 0 24 8">
          <line x1="2" y1="4" x2="22" y2="4" stroke="var(--accent-amber)" strokeWidth="3" />
        </svg>
      ),
      label: 'Contested Border',
    },
    {
      symbol: (
        <svg width="24" height="8" viewBox="0 0 24 8">
          <line x1="2" y1="4" x2="22" y2="4" stroke="var(--accent-red)" strokeWidth="2" strokeDasharray="3,5" />
        </svg>
      ),
      label: 'Risky Route',
    },
  ];

  const factionItems = Object.values(FACTION_INFO).map(f => ({
    symbol: (
      <svg width="16" height="16" viewBox="0 0 16 16">
        <circle cx="8" cy="8" r="6" fill={f.color} />
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
        borderRadius: '8px',
        backdropFilter: 'blur(8px)',
        overflow: 'hidden',
        maxWidth: isExpanded ? '280px' : '140px',
      }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--text-secondary)',
        }}
      >
        <span className="terminal-text" style={{ fontSize: '12px', fontWeight: 'bold', letterSpacing: '0.05em' }}>
          MAP LEGEND
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

      {isExpanded && (
        <div style={{ padding: '0 12px 12px', maxHeight: '400px', overflowY: 'auto' }}>
          {/* Connectivity States */}
          <Section title="Connectivity">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {connectivityItems.map((item, idx) => (
                <LegendItem key={idx} symbol={item.symbol} label={item.label} />
              ))}
            </div>
          </Section>

          {/* Content Markers */}
          <Section title="Markers">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {markerItems.map((item, idx) => (
                <LegendItem key={idx} symbol={item.symbol} label={item.label} />
              ))}
            </div>
          </Section>

          {/* Route Types */}
          <Section title="Routes">
            {routeItems.map((item, idx) => (
              <LegendItem key={idx} symbol={item.symbol} label={item.label} />
            ))}
          </Section>

          {/* Factions */}
          <Section title="Factions">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              {factionItems.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {item.symbol}
                  <span style={{ fontSize: '12px', color: item.color }}>{item.label}</span>
                </div>
              ))}
            </div>
          </Section>

          {/* Help text */}
          <div style={{ paddingTop: '8px', borderTop: '1px solid var(--border-secondary)' }}>
            <p style={{ fontSize: '10px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              Hover over regions for details. Click to select.
              Connectivity represents your social network, not geographic knowledge.
            </p>
          </div>
        </div>
      )}

      {!isExpanded && (
        <div style={{ padding: '0 12px 8px' }}>
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
      <h4 className="terminal-text" style={{ fontSize: '10px', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
        {title}
      </h4>
      {children}
    </div>
  );
}

function LegendItem({ symbol, label }: { symbol: React.ReactNode; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
      {symbol}
      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{label}</span>
    </div>
  );
}

export default MapLegend;
