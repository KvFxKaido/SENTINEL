import type { CombatIntent, CombatTargetInfo, Combatant, CombatOutcome } from './combat';
import { ACTION_LABELS, ACTION_ORDER, CombatActionType, CombatState } from './combat';
import './combat.css';

interface CombatOverlayProps {
  active: boolean;
  state: CombatState;
  round: number;
  playerId: string;
  combatants: Combatant[];
  selectedAction: CombatActionType | null;
  selectedTargetId: string | null;
  targetOptions: CombatTargetInfo[];
  intents: CombatIntent[];
  outcome: CombatOutcome | null;
  onSelectAction: (action: CombatActionType) => void;
  onSelectTarget: (targetId: string) => void;
  onClearSelection: () => void;
  onClearCombat: () => void;
}

const FACTION_COLORS: Record<string, string> = {
  steel_syndicate: '#f85149',
  ember_colonies: '#f0883e',
  ghost_protocol: '#8b949e',
  covenant: '#58a6ff',
  lattice: '#d29922',
  nexus: '#58a6ff',
  wanderers: '#6e7681',
};

function getFactionColor(faction?: string | null): string {
  if (!faction) return '#6e7681';
  return FACTION_COLORS[faction] || '#6e7681';
}

function renderInjuries(combatant: Combatant) {
  if (!combatant.injuries.length) {
    return <span className="combat-injury-none">No injuries</span>;
  }
  return combatant.injuries.map(injury => (
    <span key={`${combatant.id}-${injury.type}`} className="combat-injury-tag">
      {injury.description}
    </span>
  ));
}

export function CombatOverlay({
  active,
  state,
  round,
  playerId,
  combatants,
  selectedAction,
  selectedTargetId,
  targetOptions,
  intents,
  outcome,
  onSelectAction,
  onSelectTarget,
  onClearSelection,
  onClearCombat,
}: CombatOverlayProps) {
  if (!active) return null;

  const player = combatants.find(combatant => combatant.id === playerId);
  const enemies = combatants.filter(combatant => !combatant.isPlayer);
  const playerTurn = state === CombatState.PLAYER_TURN;

  return (
    <div className={`combat-overlay ${active ? 'active' : ''}`}>
      <div className="combat-topbar">
        <div className="combat-round">
          <span className="combat-round-label">Round</span>
          <span className="combat-round-value">{round}</span>
        </div>
        <div className="combat-turn">
          <span className={`combat-turn-indicator ${playerTurn ? 'turn-player' : 'turn-npc'}`}>
            {playerTurn ? 'Player Turn' : 'NPC Turn'}
          </span>
        </div>
        <div className="combat-turn-order">
          {combatants.map(combatant => {
            const isActive = playerTurn
              ? combatant.isPlayer
              : !combatant.isPlayer;
            const color = combatant.isPlayer ? '#56d4dd' : getFactionColor(combatant.faction);
            return (
              <span
                key={combatant.id}
                className={`combat-turn-chip ${isActive ? 'active' : ''}`}
                style={{ borderColor: color, color }}
              >
                {combatant.isPlayer ? 'PLAYER' : combatant.name.toUpperCase()}
              </span>
            );
          })}
        </div>
      </div>

      <div className="combat-panels">
        <div className="combat-panel combat-panel-actions">
          <div className="combat-panel-header">
            <span>Actions</span>
            {selectedAction && playerTurn && (
              <button className="combat-clear" onClick={onClearSelection}>
                Clear
              </button>
            )}
          </div>
          <div className="panel-actions combat-actions">
            {ACTION_ORDER.map(action => (
              <button
                key={action}
                className={`action-button ${action === selectedAction ? 'action-primary' : 'action-secondary'} ${
                  action === CombatActionType.FLEE ? 'action-danger' : ''
                }`}
                onClick={() => onSelectAction(action)}
                disabled={!playerTurn && action !== CombatActionType.FLEE}
              >
                {ACTION_LABELS[action]}
              </button>
            ))}
          </div>
          {!playerTurn && (
            <div className="combat-hint">Awaiting NPC response.</div>
          )}
        </div>

        <div className="combat-panel combat-panel-targets">
          <div className="combat-panel-header">
            <span>Targets</span>
          </div>
          {targetOptions.length === 0 ? (
            <div className="combat-empty">No targets in focus.</div>
          ) : (
            <div className="combat-target-list">
              {targetOptions.map(target => {
                const isSelected = target.id === selectedTargetId;
                const factionColor = getFactionColor(target.faction);
                return (
                  <button
                    key={target.id}
                    className={`combat-target ${isSelected ? 'selected' : ''}`}
                    onClick={() => onSelectTarget(target.id)}
                  >
                    <span className="target-name" style={{ color: factionColor }}>
                      {target.name}
                    </span>
                    <span className={`target-range ${target.inRange ? 'in-range' : 'out-range'}`}>
                      {target.distance.toFixed(1)}t
                    </span>
                    <span className={`target-cover cover-${target.coverValue}`}>
                      {target.coverValue === 2 ? 'Full' : target.coverValue === 1 ? 'Half' : 'None'}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="combat-panel combat-panel-injuries">
          <div className="combat-panel-header">
            <span>Injuries</span>
          </div>
          {player && (
            <div className="combat-injury-block">
              <div className="combat-injury-name">You</div>
              <div className="combat-injury-tags">
                {renderInjuries(player)}
              </div>
            </div>
          )}
          {enemies.map(enemy => (
            <div key={enemy.id} className="combat-injury-block">
              <div className="combat-injury-name" style={{ color: getFactionColor(enemy.faction) }}>
                {enemy.name}
              </div>
              <div className="combat-injury-tags">
                {renderInjuries(enemy)}
              </div>
            </div>
          ))}
        </div>

        <div className="combat-panel combat-panel-intents">
          <div className="combat-panel-header">
            <span>NPC Intent</span>
          </div>
          {intents.length === 0 ? (
            <div className="combat-empty">No read on intent.</div>
          ) : (
            <div className="combat-intent-list">
              {intents.map(intent => (
                <div key={intent.npcId} className="combat-intent">
                  <span className="intent-name">
                    {combatants.find(combatant => combatant.id === intent.npcId)?.name || intent.npcId}
                  </span>
                  <span className="intent-action">{ACTION_LABELS[intent.action]}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {state === CombatState.ENDED && outcome && (
        <div className="combat-outcome">
          <div className="combat-outcome-panel">
            <div className="combat-outcome-title">Combat Resolved</div>
            <div className="combat-outcome-result">{outcome.outcome.replace(/_/g, ' ')}</div>
            <button className="action-button action-primary" onClick={onClearCombat}>
              Continue
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
