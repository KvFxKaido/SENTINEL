import { useEffect, useState } from 'react';
import type { NPC, Disposition } from '../types';

interface CodecBoxProps {
  npc: NPC;
  dialogue: string;
  onClose: () => void;
}

const FACTION_COLORS: Record<string, string> = {
  nexus: 'border-faction-nexus',
  ember_colonies: 'border-faction-ember',
  ember: 'border-faction-ember',
  lattice: 'border-faction-lattice',
  convergence: 'border-faction-convergence',
  covenant: 'border-faction-covenant',
  wanderers: 'border-faction-wanderers',
  cultivators: 'border-faction-cultivators',
  steel_syndicate: 'border-faction-steel',
  steel: 'border-faction-steel',
  witnesses: 'border-faction-witnesses',
  architects: 'border-faction-architects',
  ghost_networks: 'border-faction-ghost',
  ghost: 'border-faction-ghost',
};

const FACTION_GLYPHS: Record<string, string> = {
  nexus: '◈',
  ember_colonies: '◇',
  ember: '◇',
  lattice: '⬡',
  convergence: '∞',
  covenant: '†',
  wanderers: '⊕',
  cultivators: '❀',
  steel_syndicate: '⚙',
  steel: '⚙',
  witnesses: '◉',
  architects: '△',
  ghost_networks: '◌',
  ghost: '◌',
};

const DISPOSITION_BAR: Record<Disposition, string> = {
  hostile: '▰▱▱▱▱',
  wary: '▰▰▱▱▱',
  neutral: '▰▰▰▱▱',
  warm: '▰▰▰▰▱',
  loyal: '▰▰▰▰▰',
};

const DISPOSITION_COLORS: Record<Disposition, string> = {
  hostile: 'text-sentinel-danger',
  wary: 'text-sentinel-warning',
  neutral: 'text-sentinel-secondary',
  warm: 'text-sentinel-accent',
  loyal: 'text-green-400',
};

export function CodecBox({ npc, dialogue, onClose }: CodecBoxProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  // Typewriter effect
  useEffect(() => {
    setDisplayedText('');
    setIsTyping(true);
    let index = 0;

    const interval = setInterval(() => {
      if (index < dialogue.length) {
        setDisplayedText(dialogue.slice(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(interval);
      }
    }, 30);

    return () => clearInterval(interval);
  }, [dialogue]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const factionKey = npc.faction.toLowerCase().replace(' ', '_');
  const borderColor = FACTION_COLORS[factionKey] || 'border-sentinel-border';
  const glyph = FACTION_GLYPHS[factionKey] || '◈';

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm">
      <div
        className={`w-[600px] bg-sentinel-surface border-2 ${borderColor} rounded shadow-2xl relative scan-lines`}
      >
        {/* Header */}
        <div className="p-4 border-b border-sentinel-border">
          <div className="flex items-center gap-3">
            {/* Portrait placeholder */}
            <div className={`w-16 h-16 border-2 ${borderColor} rounded flex items-center justify-center bg-sentinel-bg`}>
              <span className="text-3xl">{glyph}</span>
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sentinel-secondary font-bold text-lg">
                  {npc.name}
                </span>
              </div>
              <div className="text-sentinel-dim text-sm">
                [{npc.faction.replace('_', ' ').toUpperCase()}
                {npc.role && ` — ${npc.role}`}]
              </div>
              <div className="flex items-center gap-2 mt-1 text-xs">
                <span className="text-sentinel-dim">Disposition:</span>
                <span className={DISPOSITION_COLORS[npc.disposition]}>
                  {npc.disposition.charAt(0).toUpperCase() + npc.disposition.slice(1)}
                </span>
                <span className={`font-mono ${DISPOSITION_COLORS[npc.disposition]}`}>
                  {DISPOSITION_BAR[npc.disposition]}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Dialogue */}
        <div className="p-6">
          <p className="text-sentinel-secondary text-lg leading-relaxed">
            "{displayedText}
            {isTyping && <span className="animate-pulse">▌</span>}"
          </p>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-sentinel-border flex justify-between items-center">
          <span className="text-xs text-sentinel-dim">
            Press ESC or click to continue
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1 bg-sentinel-border text-sentinel-secondary text-sm rounded hover:bg-sentinel-dim transition-colors"
          >
            Continue
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center text-sentinel-dim hover:text-sentinel-secondary"
        >
          ×
        </button>
      </div>
    </div>
  );
}
