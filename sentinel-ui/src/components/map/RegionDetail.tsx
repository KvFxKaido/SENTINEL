import { useState } from 'react';
import type { RegionConnectivity } from './types';
import { FACTION_INFO } from './types';
import type { TravelProposal } from '../../lib/bridge';

/**
 * RegionDetail — Panel showing region info and the engine's travel assessment.
 *
 * Implements the commitment gate (Sentinel 2D §6):
 * - Engine proposes travel with full costs, requirements, risks
 * - Player reviews the ProposalResult and decides: commit, choose alternative, or cancel
 * - Cancel at any point has zero side effects
 * - Only explicit COMMIT triggers the travel action
 *
 * Data flow:
 *   MapView calls proposeTravel(regionId) → engine returns TravelProposal
 *   → this component renders the proposal → player clicks COMMIT
 *   → MapView calls commitTravel(via?) → engine resolves deterministically
 *
 * @see architecture/Sentinel 2D.md, Section 6 (Commitment Gate)
 */

interface RegionInfo {
  id: string;
  name: string;
  description: string;
  primary_faction: string;
  contested_by: string[];
  terrain: string[];
  character: string;
  connectivity: RegionConnectivity;
  position: { x: number; y: number };
}

interface RegionDetailProps {
  region: RegionInfo;
  content: { npcs: string[]; jobs: string[]; threads: string[] };
  /** Engine-computed travel proposal (null if current region or not yet loaded) */
  proposal: TravelProposal | null;
  /** Whether the proposal is being fetched from the engine */
  proposalLoading: boolean;
  /** Whether this is the player's current region */
  isCurrentRegion: boolean;
  /** Commit travel — crosses the commitment gate */
  onCommitTravel: (via?: string) => void;
  /** Cancel pending proposal — zero side effects */
  onCancelTravel: () => void;
  /** Close the detail panel */
  onClose: () => void;
  /** Whether travel is currently being resolved by the engine */
  resolving: boolean;
}

export function RegionDetail({
  region,
  content,
  proposal,
  proposalLoading,
  isCurrentRegion,
  onCommitTravel,
  onCancelTravel,
  onClose,
  resolving,
}: RegionDetailProps) {
  // Local state for the two-step confirmation (SELECT → CONFIRM)
  const [confirmVia, setConfirmVia] = useState<string | undefined>(undefined);
  const [showConfirm, setShowConfirm] = useState(false);

  const faction = FACTION_INFO[region.primary_faction as keyof typeof FACTION_INFO];

  const handleSelectDirect = () => {
    setConfirmVia(undefined);
    setShowConfirm(true);
  };

  const handleSelectAlternative = (altType: string) => {
    setConfirmVia(altType);
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    onCommitTravel(confirmVia);
    setShowConfirm(false);
  };

  const handleDismiss = () => {
    setShowConfirm(false);
    setConfirmVia(undefined);
  };

  const handleClose = () => {
    onCancelTravel();
    onClose();
  };

  // Resolve the selected alternative details for the confirmation overlay
  const selectedAlt = confirmVia && proposal
    ? proposal.alternatives.find(a => a.type === confirmVia) ?? null
    : null;

  return (
    <div className="region-detail-panel terminal-text" style={{
      position: 'absolute',
      top: '16px',
      right: '16px',
      width: '360px',
      background: 'var(--bg-panel)',
      border: '1px solid var(--border-primary)',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
      backdropFilter: 'blur(8px)',
      zIndex: 40,
      maxHeight: 'calc(100vh - 120px)',
      overflowY: 'auto',
    }}>
      {/* ── Confirmation overlay (commitment gate) ──────────────────── */}
      {showConfirm && proposal && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.9)',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '24px',
          zIndex: 50,
        }}>
          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>
              CONFIRM TRAVEL
            </div>
            <div style={{ fontSize: '14px', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
              {region.name.toUpperCase()}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              via {selectedAlt ? selectedAlt.label : 'Direct Route'}
            </div>
          </div>

          <div style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '16px',
          }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
              This action will:
            </div>
            <ConfirmCostList proposal={proposal} alternative={selectedAlt} />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={handleDismiss} style={{
              flex: 1, padding: '10px', background: 'transparent',
              border: '1px solid var(--border-primary)', borderRadius: '4px',
              color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold',
            }}>
              CANCEL
            </button>
            <button onClick={handleConfirm} style={{
              flex: 1, padding: '10px', background: 'var(--accent-steel)',
              border: 'none', borderRadius: '4px',
              color: 'black', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold',
            }}>
              COMMIT
            </button>
          </div>
        </div>
      )}

      {/* ── Resolving overlay ──────────────────────────────────────── */}
      {resolving && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.9)', borderRadius: '8px',
          display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
          padding: '24px', zIndex: 50,
        }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>
            RESOLVING
          </div>
          <div style={{ fontSize: '14px', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
            {region.name.toUpperCase()}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Engine processing turn...
          </div>
        </div>
      )}

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)', letterSpacing: '0.05em', margin: 0 }}>
            {region.name.toUpperCase()}
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0' }}>
            {region.terrain.join(' / ').toUpperCase()}
          </p>
        </div>
        <button onClick={handleClose} style={{
          background: 'transparent', border: '1px solid var(--border-primary)', borderRadius: '4px',
          color: 'var(--text-muted)', padding: '4px 8px', cursor: 'pointer', fontSize: '12px',
        }}>
          CLOSE
        </button>
      </div>

      {/* ── Faction + Connectivity ─────────────────────────────────── */}
      {faction && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: faction.color }} />
          <span style={{ fontSize: '12px', color: faction.color }}>{faction.name.toUpperCase()}</span>
          <span style={{
            fontSize: '11px', padding: '1px 6px', borderRadius: '3px', border: '1px solid',
            color: connectivityColor(region.connectivity),
            borderColor: connectivityColor(region.connectivity),
          }}>
            {region.connectivity.toUpperCase()}
          </span>
        </div>
      )}

      {/* ── Description ────────────────────────────────────────────── */}
      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '16px' }}>
        {region.description}
      </p>

      {/* ── Content summary ────────────────────────────────────────── */}
      {(content.npcs.length > 0 || content.jobs.length > 0 || content.threads.length > 0) && (
        <div style={{ marginBottom: '16px', padding: '8px', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
          {content.npcs.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-purple)', marginBottom: '4px' }}>
              NPCs: {content.npcs.join(', ')}
            </div>
          )}
          {content.jobs.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-green)', marginBottom: '4px' }}>
              Jobs: {content.jobs.join(', ')}
            </div>
          )}
          {content.threads.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-amber)' }}>
              Threads: {content.threads.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* ── Current region badge ───────────────────────────────────── */}
      {isCurrentRegion && (
        <div style={{ borderTop: '1px solid var(--border-primary)', paddingTop: '12px', fontSize: '12px', color: 'var(--accent-cyan)' }}>
          {'\u25C9'} YOU ARE HERE
        </div>
      )}

      {/* ── Travel assessment (non-current regions only) ───────────── */}
      {!isCurrentRegion && (
        <div style={{ borderTop: '1px solid var(--border-primary)', paddingTop: '12px' }}>
          <h3 style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '8px' }}>
            TRAVEL ASSESSMENT
          </h3>

          {proposalLoading && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '8px 0' }}>
              Analyzing route...
            </div>
          )}

          {proposal && !proposalLoading && (
            <ProposalView
              proposal={proposal}
              onSelectDirect={handleSelectDirect}
              onSelectAlternative={handleSelectAlternative}
            />
          )}

          {!proposal && !proposalLoading && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '8px 0' }}>
              Route assessment unavailable.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

/** Renders the full engine proposal: summary, requirements, costs, risks, options */
function ProposalView({
  proposal,
  onSelectDirect,
  onSelectAlternative,
}: {
  proposal: TravelProposal;
  onSelectDirect: () => void;
  onSelectAlternative: (type: string) => void;
}) {
  return (
    <>
      {/* Engine summary */}
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
        {proposal.summary}
      </div>

      {/* Requirements with met/unmet/bypassable status */}
      {proposal.requirements.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>REQUIREMENTS</div>
          {proposal.requirements.map((req, idx) => (
            <div key={idx} style={{
              fontSize: '12px', marginBottom: '2px', paddingLeft: '8px',
              color: req.status === 'met' ? 'var(--accent-green)' :
                     req.status === 'bypassable' ? 'var(--accent-amber)' : 'var(--accent-red)',
            }}>
              {req.status === 'met' ? '\u2713' : req.status === 'bypassable' ? '\u25C8' : '\u2717'}{' '}
              {req.label}
              {req.detail && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}> — {req.detail}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Cost preview from engine */}
      <CostPreview costs={proposal.costs} />

      {/* Risks with severity */}
      {proposal.risks.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>RISKS</div>
          {proposal.risks.map((risk, idx) => (
            <div key={idx} style={{
              fontSize: '12px', marginBottom: '2px', paddingLeft: '8px',
              color: risk.severity === 'high' ? 'var(--accent-red)' :
                     risk.severity === 'medium' ? 'var(--accent-amber)' : 'var(--text-secondary)',
            }}>
              {risk.severity === 'high' ? '\u25B2' : risk.severity === 'medium' ? '\u25C6' : '\u25C7'}{' '}
              {risk.label}
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}> — {risk.detail}</span>
            </div>
          ))}
        </div>
      )}

      {/* Direct route option (only if feasible) */}
      {proposal.feasible && (
        <TravelOption
          label="Direct Route"
          description="All requirements met"
          available={true}
          onSelect={onSelectDirect}
        />
      )}

      {/* Blocked indicator + alternatives */}
      {!proposal.feasible && proposal.alternatives.length > 0 && (
        <div style={{ fontSize: '12px', color: 'var(--accent-red)', marginBottom: '8px' }}>
          DIRECT ROUTE BLOCKED
        </div>
      )}

      {proposal.alternatives.map((alt, idx) => (
        <TravelOption
          key={idx}
          label={alt.label}
          description={alt.description}
          cost={alt.costs}
          consequence={alt.consequence}
          available={true}
          onSelect={() => onSelectAlternative(alt.type)}
        />
      ))}

      {/* Completely blocked — no alternatives either */}
      {!proposal.feasible && proposal.alternatives.length === 0 && (
        <div style={{
          fontSize: '12px', color: 'var(--accent-red)', marginTop: '8px', padding: '8px',
          background: 'rgba(248,81,73,0.1)', borderRadius: '4px',
        }}>
          No viable route from current location.
        </div>
      )}
    </>
  );
}

/** Displays the engine's cost preview — turns, fuel, condition, social energy, credits, standing */
function CostPreview({ costs }: { costs: TravelProposal['costs'] }) {
  const items: Array<{ label: string; value: string; color: string }> = [];

  if (costs.turns > 0)
    items.push({ label: 'Turns', value: String(costs.turns), color: 'var(--text-secondary)' });
  if (costs.fuel > 0)
    items.push({ label: 'Fuel', value: `-${costs.fuel}`, color: 'var(--accent-amber)' });
  if (costs.condition > 0)
    items.push({ label: 'Condition', value: `-${costs.condition}`, color: 'var(--accent-amber)' });
  if (costs.social_energy > 0)
    items.push({ label: 'Social Energy', value: `-${costs.social_energy}`, color: 'var(--accent-amber)' });
  if (costs.credits > 0)
    items.push({ label: 'Credits', value: `-${costs.credits}`, color: 'var(--accent-amber)' });

  for (const [factionId, delta] of Object.entries(costs.standing_changes)) {
    if (delta !== 0) {
      const sign = delta > 0 ? '+' : '';
      items.push({
        label: factionId.replace(/_/g, ' '),
        value: `${sign}${delta}`,
        color: delta > 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      });
    }
  }

  if (items.length === 0) return null;

  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>COSTS</div>
      {items.map((item, idx) => (
        <div key={idx} style={{
          fontSize: '12px', marginBottom: '2px', paddingLeft: '8px',
          display: 'flex', justifyContent: 'space-between', color: item.color,
        }}>
          <span>{item.label}</span>
          <span style={{ fontFamily: 'var(--font-mono)' }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

/** Itemized cost list for the confirmation overlay */
function ConfirmCostList({
  proposal,
  alternative,
}: {
  proposal: TravelProposal;
  alternative: TravelProposal['alternatives'][number] | null;
}) {
  const items: Array<{ text: string; danger: boolean }> = [];

  const turns = proposal.costs.turns || 1;
  items.push({ text: `Consume ${turns} turn${turns > 1 ? 's' : ''}`, danger: false });

  if (proposal.costs.fuel > 0)
    items.push({ text: `Use ${proposal.costs.fuel} fuel`, danger: false });
  if (proposal.costs.condition > 0)
    items.push({ text: `Wear ${proposal.costs.condition} condition`, danger: false });

  // Alternative costs override base costs for social/credits
  if (alternative) {
    if (alternative.costs.social_energy > 0)
      items.push({ text: `Drain ${alternative.costs.social_energy} social energy`, danger: false });
    if (alternative.costs.credits > 0)
      items.push({ text: `Spend ${alternative.costs.credits} credits`, danger: false });
    if (alternative.consequence)
      items.push({ text: `Risk: ${alternative.consequence.replace(/_/g, ' ')}`, danger: true });
  } else {
    if (proposal.costs.social_energy > 0)
      items.push({ text: `Drain ${proposal.costs.social_energy} social energy`, danger: false });
    if (proposal.costs.credits > 0)
      items.push({ text: `Spend ${proposal.costs.credits} credits`, danger: false });
  }

  // Standing changes
  for (const [factionId, delta] of Object.entries(proposal.costs.standing_changes)) {
    if (delta !== 0) {
      const label = factionId.replace(/_/g, ' ');
      const sign = delta > 0 ? '+' : '';
      items.push({ text: `${label} standing ${sign}${delta}`, danger: delta < 0 });
    }
  }

  return (
    <>
      {items.map((item, idx) => (
        <div key={idx} style={{
          fontSize: '12px',
          color: item.danger ? 'var(--accent-red)' : 'var(--accent-amber)',
          marginBottom: '4px',
        }}>
          {'\u2022'} {item.text}
        </div>
      ))}
    </>
  );
}

/** Single travel option card (direct or alternative) */
function TravelOption({
  label,
  description,
  cost,
  consequence,
  available,
  onSelect,
}: {
  label: string;
  description: string;
  cost?: { turns?: number; social_energy?: number; credits?: number };
  consequence?: string | null;
  available: boolean;
  onSelect: () => void;
}) {
  const costParts = cost
    ? [
        cost.turns && cost.turns > 0 ? `${cost.turns} turn${cost.turns > 1 ? 's' : ''}` : null,
        cost.social_energy && cost.social_energy > 0 ? `${cost.social_energy} social energy` : null,
        cost.credits && cost.credits > 0 ? `${cost.credits} credits` : null,
      ].filter(Boolean)
    : [];

  return (
    <div style={{
      padding: '8px', marginBottom: '6px', background: 'var(--bg-tertiary)',
      border: `1px solid ${available ? 'var(--border-primary)' : 'var(--border-secondary)'}`,
      borderRadius: '4px', opacity: available ? 1 : 0.5,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', fontWeight: 'bold', color: available ? 'var(--text-primary)' : 'var(--text-muted)' }}>
          {label}
        </span>
        {available && (
          <button onClick={onSelect} style={{
            fontSize: '11px', padding: '2px 8px', background: 'var(--accent-steel)',
            color: 'black', border: 'none', borderRadius: '3px', cursor: 'pointer', fontWeight: 'bold',
          }}>
            SELECT
          </button>
        )}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
        {description}
      </div>
      {costParts.length > 0 && (
        <div style={{ fontSize: '11px', color: 'var(--accent-amber)', marginTop: '4px' }}>
          Cost: {costParts.join(', ')}
        </div>
      )}
      {consequence && (
        <div style={{ fontSize: '11px', color: 'var(--accent-red)', marginTop: '2px' }}>
          Risk: {consequence.replace(/_/g, ' ')}
        </div>
      )}
    </div>
  );
}

function connectivityColor(connectivity: RegionConnectivity): string {
  switch (connectivity) {
    case 'disconnected': return 'var(--text-muted)';
    case 'aware': return 'var(--state-aware)';
    case 'connected': return 'var(--state-connected)';
    case 'embedded': return 'var(--state-embedded)';
    default: return 'var(--text-muted)';
  }
}

export default RegionDetail;
