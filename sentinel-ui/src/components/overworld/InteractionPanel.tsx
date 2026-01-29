/**
 * InteractionPanel — Panel for entity interactions
 * 
 * Shows detailed information and action options for entities.
 * All meaningful actions pass through the commitment gate.
 */

import { useState } from 'react';
import type { Entity, NPCData, HazardData, POIData, ExitData } from './types';
import './overworld.css';

interface InteractionPanelProps {
  entity: Entity | null;
  onAction: (action: string, params?: Record<string, unknown>) => void;
  onClose: () => void;
}

export function InteractionPanel({ entity, onAction, onClose }: InteractionPanelProps) {
  const [confirming, setConfirming] = useState<string | null>(null);

  if (!entity) return null;

  const handleAction = (action: string) => {
    if (requiresConfirmation(entity.type, action)) {
      setConfirming(action);
    } else {
      onAction(action);
      onClose();
    }
  };

  const handleConfirm = () => {
    if (confirming) {
      onAction(confirming);
      setConfirming(null);
      onClose();
    }
  };

  const handleCancel = () => {
    setConfirming(null);
  };

  return (
    <div className="interaction-panel">
      <div className="interaction-header">
        <span className="interaction-type">{getTypeLabel(entity.type)}</span>
        <button className="interaction-close" onClick={onClose}>×</button>
      </div>

      <div className="interaction-content">
        {confirming ? (
          <ConfirmationDialog
            entity={entity}
            action={confirming}
            onConfirm={handleConfirm}
            onCancel={handleCancel}
          />
        ) : (
          <EntityDetails entity={entity} onAction={handleAction} />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Entity Details
// ============================================================================

function EntityDetails({
  entity,
  onAction,
}: {
  entity: Entity;
  onAction: (action: string) => void;
}) {
  switch (entity.type) {
    case 'npc':
      return <NPCDetails entity={entity} onAction={onAction} />;
    case 'hazard':
      return <HazardDetails entity={entity} onAction={onAction} />;
    case 'poi':
      return <POIDetails entity={entity} onAction={onAction} />;
    case 'exit':
      return <ExitDetails entity={entity} onAction={onAction} />;
    default:
      return null;
  }
}

function NPCDetails({
  entity,
  onAction,
}: {
  entity: Entity;
  onAction: (action: string) => void;
}) {
  const data = entity.data as NPCData;

  return (
    <div className="entity-details">
      <h3 className="entity-name">{entity.label}</h3>
      
      {data.faction && (
        <div className="entity-meta">
          <span className="meta-label">Faction:</span>
          <span className="meta-value">{data.faction}</span>
        </div>
      )}
      
      <div className="entity-meta">
        <span className="meta-label">Disposition:</span>
        <span className={`meta-value disposition-${data.disposition}`}>
          {data.disposition}
        </span>
      </div>

      <div className="entity-actions">
        <button className="action-button" onClick={() => onAction('talk')}>
          Talk
        </button>
        <button className="action-button" onClick={() => onAction('observe')}>
          Observe
        </button>
        {data.disposition !== 'hostile' && (
          <button className="action-button" onClick={() => onAction('trade')}>
            Trade
          </button>
        )}
      </div>

      <p className="interaction-hint">
        Talking may reveal information or advance relationships.
        This does not consume a turn unless you commit to an action.
      </p>
    </div>
  );
}

function HazardDetails({
  entity,
  onAction,
}: {
  entity: Entity;
  onAction: (action: string) => void;
}) {
  const data = entity.data as HazardData;

  return (
    <div className="entity-details">
      <h3 className="entity-name">{entity.label}</h3>
      
      <div className="entity-meta">
        <span className="meta-label">Severity:</span>
        <span className={`meta-value severity-${data.severity}`}>
          {data.severity}
        </span>
      </div>

      <div className="entity-meta">
        <span className="meta-label">Terrain:</span>
        <span className="meta-value">{data.terrain}</span>
      </div>

      <div className="entity-actions">
        <button className="action-button" onClick={() => onAction('assess')}>
          Assess Risk
        </button>
        <button className="action-button action-risky" onClick={() => onAction('bypass')}>
          Attempt Bypass
        </button>
        <button className="action-button" onClick={() => onAction('avoid')}>
          Find Another Way
        </button>
      </div>

      <p className="interaction-hint hazard-warning">
        Bypassing hazards may have consequences.
        Assess the risk before committing.
      </p>
    </div>
  );
}

function POIDetails({
  entity,
  onAction,
}: {
  entity: Entity;
  onAction: (action: string) => void;
}) {
  const data = entity.data as POIData;

  return (
    <div className="entity-details">
      <h3 className="entity-name">{entity.label}</h3>
      
      <p className="entity-description">{data.description}</p>

      <div className="entity-actions">
        <button className="action-button" onClick={() => onAction('investigate')}>
          Investigate
        </button>
        {data.interactable && (
          <button className="action-button" onClick={() => onAction('interact')}>
            Interact
          </button>
        )}
        <button className="action-button" onClick={() => onAction('search')}>
          Search Area
        </button>
      </div>

      <p className="interaction-hint">
        Investigation may reveal items, information, or opportunities.
      </p>
    </div>
  );
}

function ExitDetails({
  entity,
  onAction,
}: {
  entity: Entity;
  onAction: (action: string) => void;
}) {
  const data = entity.data as ExitData;

  return (
    <div className="entity-details">
      <h3 className="entity-name">Exit to {entity.label}</h3>
      
      <div className="entity-meta">
        <span className="meta-label">Direction:</span>
        <span className="meta-value">{data.direction}</span>
      </div>

      <div className="entity-meta">
        <span className="meta-label">Status:</span>
        <span className={`meta-value ${data.traversable ? 'status-open' : 'status-blocked'}`}>
          {data.traversable ? 'Traversable' : 'Blocked'}
        </span>
      </div>

      {!data.traversable && data.blocked_reason && (
        <p className="blocked-reason">{data.blocked_reason}</p>
      )}

      <div className="entity-actions">
        {data.traversable ? (
          <button className="action-button action-commit" onClick={() => onAction('travel')}>
            Travel (1 turn)
          </button>
        ) : (
          <button className="action-button" disabled>
            Route Blocked
          </button>
        )}
        <button className="action-button" onClick={() => onAction('scout')}>
          Scout Ahead
        </button>
      </div>

      <p className="interaction-hint">
        Traveling to another region consumes one turn and may have consequences.
      </p>
    </div>
  );
}

// ============================================================================
// Confirmation Dialog
// ============================================================================

function ConfirmationDialog({
  entity,
  action,
  onConfirm,
  onCancel,
}: {
  entity: Entity;
  action: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { title, description, cost, consequence } = getConfirmationDetails(entity, action);

  return (
    <div className="confirmation-dialog">
      <h3 className="confirmation-title">{title}</h3>
      <p className="confirmation-description">{description}</p>

      {cost && (
        <div className="confirmation-cost">
          <span className="cost-label">Cost:</span>
          <span className="cost-value">{cost}</span>
        </div>
      )}

      {consequence && (
        <div className="confirmation-consequence">
          <span className="consequence-label">Consequence:</span>
          <span className="consequence-value">{consequence}</span>
        </div>
      )}

      <div className="confirmation-actions">
        <button className="action-button action-cancel" onClick={onCancel}>
          Cancel
        </button>
        <button className="action-button action-confirm" onClick={onConfirm}>
          Confirm
        </button>
      </div>

      <p className="confirmation-warning">
        This action passes through the commitment gate and cannot be undone.
      </p>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getTypeLabel(type: Entity['type']): string {
  switch (type) {
    case 'npc': return '● NPC';
    case 'hazard': return '⚠ HAZARD';
    case 'poi': return '◆ POINT OF INTEREST';
    case 'exit': return '→ EXIT';
    default: return 'ENTITY';
  }
}

function requiresConfirmation(type: Entity['type'], action: string): boolean {
  // Actions that pass through the commitment gate
  const commitActions: Record<string, string[]> = {
    npc: ['trade', 'threaten', 'recruit'],
    hazard: ['bypass'],
    poi: ['interact'],
    exit: ['travel'],
  };

  return commitActions[type]?.includes(action) || false;
}

function getConfirmationDetails(
  entity: Entity,
  action: string
): {
  title: string;
  description: string;
  cost?: string;
  consequence?: string;
} {
  switch (action) {
    case 'travel':
      return {
        title: `Travel to ${entity.label}?`,
        description: 'This will move you to the selected region.',
        cost: '1 turn',
        consequence: 'Region change',
      };
    case 'bypass':
      return {
        title: `Bypass ${entity.label}?`,
        description: 'Attempting to bypass this hazard carries risk.',
        cost: 'Social energy',
        consequence: 'Possible injury or detection',
      };
    case 'trade':
      return {
        title: `Trade with ${entity.label}?`,
        description: 'Open trade interface with this NPC.',
        cost: undefined,
        consequence: 'May affect standing',
      };
    case 'interact':
      return {
        title: `Interact with ${entity.label}?`,
        description: 'This may trigger events or consequences.',
        cost: undefined,
        consequence: 'Unknown',
      };
    default:
      return {
        title: `Confirm ${action}?`,
        description: 'This action will be committed.',
      };
  }
}
