import type { GameState, Disposition } from '../types';

interface SidebarProps {
  gameState: GameState;
}

const FACTION_DISPLAY: Record<string, string> = {
  nexus: 'Nexus',
  ember_colonies: 'Ember Colonies',
  lattice: 'Lattice',
  convergence: 'Convergence',
  covenant: 'Covenant',
  wanderers: 'Wanderers',
  cultivators: 'Cultivators',
  steel_syndicate: 'Steel Syndicate',
  witnesses: 'Witnesses',
  architects: 'Architects',
  ghost_networks: 'Ghost Networks',
};

const DISPOSITION_COLORS: Record<Disposition, string> = {
  hostile: 'text-sentinel-danger',
  wary: 'text-sentinel-warning',
  neutral: 'text-sentinel-secondary',
  warm: 'text-sentinel-accent',
  loyal: 'text-green-400',
};

const DISPOSITION_BAR: Record<Disposition, string> = {
  hostile: '▰▱▱▱▱',
  wary: '▰▰▱▱▱',
  neutral: '▰▰▰▱▱',
  warm: '▰▰▰▰▱',
  loyal: '▰▰▰▰▰',
};

function SocialEnergyMeter({ value }: { value: number }) {
  const getColor = () => {
    if (value > 50) return 'bg-sentinel-accent';
    if (value > 25) return 'bg-sentinel-warning';
    return 'bg-sentinel-danger';
  };

  const getLabel = () => {
    if (value > 50) return 'Centered';
    if (value > 25) return 'Frayed';
    if (value > 0) return 'Overloaded';
    return 'Shutdown';
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-sentinel-dim">Social Energy</span>
        <span className={value > 50 ? 'text-sentinel-accent' : value > 25 ? 'text-sentinel-warning' : 'text-sentinel-danger'}>
          {getLabel()}
        </span>
      </div>
      <div className="h-2 bg-sentinel-bg rounded overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all duration-500`}
          style={{ width: `${value}%` }}
        />
      </div>
      <div className="text-right text-xs text-sentinel-dim">{value}%</div>
    </div>
  );
}

export function Sidebar({ gameState }: SidebarProps) {
  const { character, factions, loadout } = gameState;

  return (
    <aside className="w-64 bg-sentinel-surface border-r border-sentinel-border flex flex-col">
      {/* Character Info */}
      <section className="p-4 border-b border-sentinel-border">
        <h2 className="text-sentinel-accent font-bold text-sm tracking-wider mb-3">
          OPERATIVE
        </h2>
        <div className="space-y-2">
          <div>
            <div className="text-sentinel-secondary font-bold">{character.name}</div>
            <div className="text-sentinel-dim text-xs">{character.background}</div>
          </div>
          <SocialEnergyMeter value={character.socialEnergy} />
        </div>
      </section>

      {/* Loadout */}
      <section className="p-4 border-b border-sentinel-border">
        <h2 className="text-sentinel-accent font-bold text-sm tracking-wider mb-3">
          LOADOUT
        </h2>
        <ul className="space-y-1 text-sm">
          {loadout.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sentinel-secondary">
              <span className="text-sentinel-dim">•</span>
              {item}
            </li>
          ))}
          {loadout.length === 0 && (
            <li className="text-sentinel-dim italic">No gear selected</li>
          )}
        </ul>
      </section>

      {/* Faction Standings */}
      <section className="p-4 flex-1 overflow-y-auto">
        <h2 className="text-sentinel-accent font-bold text-sm tracking-wider mb-3">
          FACTIONS
        </h2>
        <ul className="space-y-2 text-sm">
          {Object.entries(factions).map(([factionId, disposition]) => (
            <li key={factionId} className="flex justify-between items-center">
              <span className="text-sentinel-secondary">
                {FACTION_DISPLAY[factionId] || factionId}
              </span>
              <span className={`font-mono text-xs ${DISPOSITION_COLORS[disposition]}`}>
                {DISPOSITION_BAR[disposition]}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Quick commands */}
      <section className="p-4 border-t border-sentinel-border">
        <div className="text-xs text-sentinel-dim space-y-1">
          <div><span className="text-sentinel-accent">/status</span> - View status</div>
          <div><span className="text-sentinel-accent">/loadout</span> - Manage gear</div>
          <div><span className="text-sentinel-accent">/help</span> - Commands</div>
        </div>
      </section>
    </aside>
  );
}
