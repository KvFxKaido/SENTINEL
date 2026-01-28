import { useState } from 'react';
import { factions } from '@/data/factions';

export const MapLegend = () => {
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

  const factionItems = Object.values(factions).map(f => ({
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
      className="absolute bottom-4 left-4 bg-black/90 border border-[var(--border-primary)] rounded-lg backdrop-blur-sm overflow-hidden"
      style={{ maxWidth: isExpanded ? '280px' : '140px' }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-[var(--bg-tertiary)] transition-colors"
      >
        <span className="text-xs font-bold text-[var(--text-secondary)] tracking-wider terminal-text">
          MAP LEGEND
        </span>
        <svg 
          width="12" 
          height="12" 
          viewBox="0 0 12 12" 
          className="transition-transform"
          style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          <path d="M2 4 L6 8 L10 4" stroke="var(--text-muted)" strokeWidth="1.5" fill="none" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-4 max-h-[400px] overflow-y-auto">
          {/* Connectivity States */}
          <div>
            <h4 className="text-[10px] font-bold text-[var(--text-muted)] mb-2 tracking-wider uppercase">
              Connectivity
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {connectivityItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  {item.symbol}
                  <span className="text-xs text-[var(--text-secondary)]">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Content Markers */}
          <div>
            <h4 className="text-[10px] font-bold text-[var(--text-muted)] mb-2 tracking-wider uppercase">
              Markers
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {markerItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  {item.symbol}
                  <span className="text-xs text-[var(--text-secondary)]">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Route Types */}
          <div>
            <h4 className="text-[10px] font-bold text-[var(--text-muted)] mb-2 tracking-wider uppercase">
              Routes
            </h4>
            <div className="space-y-1.5">
              {routeItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  {item.symbol}
                  <span className="text-xs text-[var(--text-secondary)]">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Factions */}
          <div>
            <h4 className="text-[10px] font-bold text-[var(--text-muted)] mb-2 tracking-wider uppercase">
              Factions
            </h4>
            <div className="grid grid-cols-2 gap-1.5">
              {factionItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  {item.symbol}
                  <span className="text-xs" style={{ color: item.color }}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Help text */}
          <div className="pt-2 border-t border-[var(--border-secondary)]">
            <p className="text-[10px] text-[var(--text-muted)] leading-relaxed">
              Hover over regions for details. Click to select. 
              Connectivity represents your social network, not geographic knowledge.
            </p>
          </div>
        </div>
      )}

      {!isExpanded && (
        <div className="px-3 pb-2">
          <p className="text-[10px] text-[var(--text-muted)]">
            Click to expand
          </p>
        </div>
      )}
    </div>
  );
};

export default MapLegend;
