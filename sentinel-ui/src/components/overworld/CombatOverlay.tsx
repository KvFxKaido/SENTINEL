/**
 * CombatOverlay — Turn-based combat UI
 * 
 * Combat is always a commitment:
 * - Overworld movement freezes
 * - Combat resolves fully turn-based
 * - Consequences cascade into campaign state
 * - Control returns to spatial layer after resolution
 * 
 * There is no real-time combat resolution.
 */

import { useState, useCallback } from 'react';
import type { 
  CombatState, 
  Combatant, 
  CombatAction,
  CombatLogEntry,
  CombatOutcome,
} from './expansion-types';
import { PLAYER_ACTIONS, FACTION_COLORS } from './expansion-types';
import './overworld.css';

interface CombatOverlayProps {
  combat: CombatState;
  onAction: (action: CombatAction, targetId?: string) => void;
  onEnd: (outcome: CombatOutcome) => void;
}

export function CombatOverlay({ combat, onAction, onEnd }: CombatOverlayProps) {
  const [selectedAction, setSelectedAction] = useState<CombatAction | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);

  const player = combat.combatants.find(c => c.type === 'player');
  const enemies = combat.combatants.filter(c => c.type === 'hostile');
  const isPlayerTurn = combat.phase === 'player_turn';

  const handleActionSelect = useCallback((action: CombatAction) => {
    setSelectedAction(action);
    
    // Self-targeting actions execute immediately
    if (action.targetType === 'self') {
      onAction(action);
      setSelectedAction(null);
    }
  }, [onAction]);

  const handleTargetSelect = useCallback((targetId: string) => {
    if (selectedAction && selectedAction.targetType === 'single') {
      onAction(selectedAction, targetId);
      setSelectedAction(null);
      setSelectedTarget(null);
    }
  }, [selectedAction, onAction]);

  const handleEndCombat = useCallback(() => {
    if (combat.outcome) {
      onEnd(combat.outcome);
    }
  }, [combat.outcome, onEnd]);

  // Combat ended
  if (combat.outcome) {
    return (
      <div className="combat-overlay">
        <div className="combat-outcome">
          <h2 className={`outcome-title ${combat.outcome.victory ? 'victory' : 'defeat'}`}>
            {combat.outcome.victory ? 'VICTORY' : combat.outcome.fled ? 'ESCAPED' : 'DEFEATED'}
          </h2>
          
          {combat.outcome.consequences.length > 0 && (
            <div className="outcome-section">
              <h3>Consequences</h3>
              <ul>
                {combat.outcome.consequences.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {combat.outcome.rewards && combat.outcome.rewards.length > 0 && (
            <div className="outcome-section">
              <h3>Rewards</h3>
              <ul>
                {combat.outcome.rewards.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          <button className="combat-end-button" onClick={handleEndCombat}>
            Continue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="combat-overlay">
      <div className="combat-header">
        <span className="combat-turn">TURN {combat.turn}</span>
        <span className="combat-phase">
          {combat.phase === 'player_turn' ? 'YOUR TURN' : 'ENEMY TURN'}
        </span>
      </div>

      <div className="combat-arena">
        {/* Player side */}
        <div className="combat-side player-side">
          {player && (
            <CombatantCard 
              combatant={player} 
              isActive={isPlayerTurn}
              isTargetable={false}
            />
          )}
        </div>

        {/* VS indicator */}
        <div className="combat-vs">VS</div>

        {/* Enemy side */}
        <div className="combat-side enemy-side">
          {enemies.map(enemy => (
            <CombatantCard
              key={enemy.id}
              combatant={enemy}
              isActive={combat.currentCombatant === enemy.id}
              isTargetable={isPlayerTurn && selectedAction?.targetType === 'single'}
              onSelect={() => handleTargetSelect(enemy.id)}
              isSelected={selectedTarget === enemy.id}
            />
          ))}
        </div>
      </div>

      {/* Action panel */}
      {isPlayerTurn && player && (
        <div className="combat-actions">
          <div className="actions-header">SELECT ACTION</div>
          <div className="actions-list">
            {PLAYER_ACTIONS.map(action => (
              <button
                key={action.id}
                className={`action-button ${selectedAction?.id === action.id ? 'selected' : ''}`}
                onClick={() => handleActionSelect(action)}
                disabled={action.cost > player.energy}
              >
                <span className="action-name">{action.name}</span>
                <span className="action-cost">{action.cost} EN</span>
                <span className="action-desc">{action.description}</span>
              </button>
            ))}
          </div>
          
          {selectedAction && selectedAction.targetType === 'single' && (
            <div className="target-prompt">
              Select a target for {selectedAction.name}
            </div>
          )}
        </div>
      )}

      {/* Combat log */}
      <div className="combat-log">
        <div className="log-header">COMBAT LOG</div>
        <div className="log-entries">
          {combat.log.slice(-5).map((entry, i) => (
            <LogEntry key={i} entry={entry} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Combatant Card
// ============================================================================

interface CombatantCardProps {
  combatant: Combatant;
  isActive: boolean;
  isTargetable: boolean;
  isSelected?: boolean;
  onSelect?: () => void;
}

function CombatantCard({ 
  combatant, 
  isActive, 
  isTargetable,
  isSelected,
  onSelect,
}: CombatantCardProps) {
  const healthPercent = (combatant.health / combatant.maxHealth) * 100;
  const energyPercent = (combatant.energy / combatant.maxEnergy) * 100;
  const factionColor = combatant.faction ? FACTION_COLORS[combatant.faction] : '#8b949e';

  return (
    <div 
      className={`combatant-card ${isActive ? 'active' : ''} ${isTargetable ? 'targetable' : ''} ${isSelected ? 'selected' : ''}`}
      onClick={isTargetable ? onSelect : undefined}
      style={{ borderColor: isActive ? factionColor : undefined }}
    >
      <div className="combatant-name">{combatant.name}</div>
      
      {combatant.faction && (
        <div className="combatant-faction" style={{ color: factionColor }}>
          {combatant.faction.replace(/_/g, ' ')}
        </div>
      )}

      <div className="combatant-bars">
        <div className="stat-bar health-bar">
          <div className="bar-label">HP</div>
          <div className="bar-track">
            <div 
              className="bar-fill" 
              style={{ 
                width: `${healthPercent}%`,
                backgroundColor: healthPercent > 50 ? '#3fb950' : healthPercent > 25 ? '#d29922' : '#f85149',
              }}
            />
          </div>
          <div className="bar-value">{combatant.health}/{combatant.maxHealth}</div>
        </div>

        <div className="stat-bar energy-bar">
          <div className="bar-label">EN</div>
          <div className="bar-track">
            <div 
              className="bar-fill" 
              style={{ 
                width: `${energyPercent}%`,
                backgroundColor: '#58a6ff',
              }}
            />
          </div>
          <div className="bar-value">{combatant.energy}/{combatant.maxEnergy}</div>
        </div>
      </div>

      {isTargetable && (
        <div className="target-indicator">⊕ TARGET</div>
      )}
    </div>
  );
}

// ============================================================================
// Log Entry
// ============================================================================

function LogEntry({ entry }: { entry: CombatLogEntry }) {
  return (
    <div className="log-entry">
      <span className="log-turn">[{entry.turn}]</span>
      <span className="log-actor">{entry.actor}</span>
      <span className="log-action">{entry.action}</span>
      {entry.target && <span className="log-target">→ {entry.target}</span>}
      <span className="log-result">{entry.result}</span>
      {entry.damage !== undefined && (
        <span className="log-damage">-{entry.damage} HP</span>
      )}
    </div>
  );
}

// ============================================================================
// Combat State Management
// ============================================================================

export function createInitialCombatState(
  playerName: string,
  playerHealth: number,
  playerEnergy: number,
  enemies: Array<{ name: string; health: number; faction?: string }>
): CombatState {
  const combatants: Combatant[] = [
    {
      id: 'player',
      name: playerName,
      type: 'player',
      health: playerHealth,
      maxHealth: playerHealth,
      energy: playerEnergy,
      maxEnergy: playerEnergy,
      position: { x: 0, y: 0 },
    },
    ...enemies.map((enemy, i) => ({
      id: `enemy-${i}`,
      name: enemy.name,
      type: 'hostile' as const,
      health: enemy.health,
      maxHealth: enemy.health,
      energy: 3,
      maxEnergy: 3,
      position: { x: 0, y: 0 },
      faction: enemy.faction,
    })),
  ];

  return {
    active: true,
    phase: 'player_turn',
    turn: 1,
    combatants,
    currentCombatant: 'player',
    selectedAction: null,
    selectedTarget: null,
    log: [{
      turn: 1,
      actor: 'System',
      action: 'Combat initiated',
      result: `${enemies.length} hostile${enemies.length !== 1 ? 's' : ''} engaged`,
    }],
    outcome: null,
  };
}

export function processCombatAction(
  state: CombatState,
  action: CombatAction,
  targetId?: string
): CombatState {
  const newState = { ...state };
  const actor = newState.combatants.find(c => c.id === newState.currentCombatant);
  
  if (!actor) return state;

  // Deduct energy cost
  actor.energy = Math.max(0, actor.energy - action.cost);

  // Process action
  const logEntry: CombatLogEntry = {
    turn: newState.turn,
    actor: actor.name,
    action: action.name,
    result: '',
  };

  switch (action.type) {
    case 'attack': {
      const target = newState.combatants.find(c => c.id === targetId);
      if (target) {
        const damage = Math.floor(Math.random() * 10) + 5;
        target.health = Math.max(0, target.health - damage);
        logEntry.target = target.name;
        logEntry.result = 'Hit!';
        logEntry.damage = damage;
      }
      break;
    }
    case 'defend': {
      logEntry.result = 'Defending';
      break;
    }
    case 'flee': {
      const success = Math.random() > 0.3;
      if (success) {
        newState.outcome = {
          victory: false,
          fled: true,
          consequences: ['Escaped combat'],
        };
        logEntry.result = 'Escaped!';
      } else {
        logEntry.result = 'Failed to escape';
      }
      break;
    }
    default:
      logEntry.result = 'Used';
  }

  newState.log = [...newState.log, logEntry];

  // Check for victory/defeat
  const player = newState.combatants.find(c => c.type === 'player');
  const aliveEnemies = newState.combatants.filter(c => c.type === 'hostile' && c.health > 0);

  if (player && player.health <= 0) {
    newState.outcome = {
      victory: false,
      fled: false,
      consequences: ['Defeated in combat'],
      casualties: [player.name],
    };
  } else if (aliveEnemies.length === 0) {
    newState.outcome = {
      victory: true,
      fled: false,
      consequences: [],
      rewards: ['Combat experience'],
    };
  } else if (!newState.outcome) {
    // Advance turn
    if (actor.type === 'player') {
      newState.phase = 'enemy_turn';
      newState.currentCombatant = aliveEnemies[0]?.id || null;
    } else {
      const currentIndex = aliveEnemies.findIndex(e => e.id === actor.id);
      if (currentIndex < aliveEnemies.length - 1) {
        newState.currentCombatant = aliveEnemies[currentIndex + 1].id;
      } else {
        newState.phase = 'player_turn';
        newState.currentCombatant = 'player';
        newState.turn += 1;
        // Restore some energy each turn
        if (player) {
          player.energy = Math.min(player.maxEnergy, player.energy + 2);
        }
      }
    }
  }

  return newState;
}
