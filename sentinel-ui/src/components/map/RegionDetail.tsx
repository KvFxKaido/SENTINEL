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
      width: '380px',
      maxHeight: 'calc(100vh - 120px)',
      overflowY: 'auto',
      zIndex: 40,
      padding: '20px',
    }}>
      {/* ── Confirmation overlay (commitment gate) ──────────────────── */}
      {showConfirm && proposal && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.92)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '24px',
          zIndex: 50,
          backdropFilter: 'blur(8px)',
        }}>
          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <div style={{ 
              fontSize: '10px', 
              color: 'var(--text-muted)', 
              letterSpacing: '0.15em', 
              marginBottom: '12px',
              textTransform: 'uppercase',
            }}>
              Confirm Travel
            </div>
            <div style={{ 
              fontSize: '18px', 
              color: 'var(--accent-cyan)', 
              fontWeight: 'bold',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
            }}>
              {region.name}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
              via {selectedAlt ? selectedAlt.label : 'Direct Route'}
            </div>
          </div>

          <div style={{
            background: 'rgba(18, 18, 18, 0.8)',
            border: '1px solid var(--border-primary)',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '20px',
          }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              This action will:
            </div>
            <ConfirmCostList proposal={proposal} alternative={selectedAlt} />
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button onClick={handleDismiss} style={{
              flex: 1, 
              padding: '12px', 
              background: 'transparent',
              border: '1px solid var(--border-primary)', 
              borderRadius: '6px',
              color: 'var(--text-secondary)', 
              cursor: 'pointer', 
              fontSize: '12px', 
              fontWeight: 'bold',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              transition: 'all 0.15s ease',
            }}>
              Cancel
            </button>
            <button onClick={handleConfirm} style={{
              flex: 1, 
              padding: '12px', 
              background: 'linear-gradient(135deg, var(--accent-steel), var(--accent-cyan))',
              border: 'none', 
              borderRadius: '6px',
              color: 'black', 
              cursor: 'pointer', 
              fontSize: '12px', 
              fontWeight: 'bold',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              boxShadow: '0 4px 12px rgba(86, 212, 221, 0.3)',
              transition: 'all 0.15s ease',
            }}>
              Commit
            </button>
          </div>
        </div>
      )}

      {/* ── Resolving overlay ──────────────────────────────────────── */}
      {resolving && (
        <div style={{
          position: 'absolute', 
          inset: 0, 
          background: 'rgba(0,0,0,0.92)', 
          borderRadius: '12px',
          display: 'flex', 
          flexDirection: 'column', 
          justifyContent: 'center', 
          alignItems: 'center',
          padding: '24px', 
          zIndex: 50,
          backdropFilter: 'blur(8px)',
        }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            border: '2px solid var(--bg-tertiary)',
            borderTopColor: 'var(--accent-cyan)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            marginBottom: '16px',
          }} />
          <div style={{ 
            fontSize: '10px', 
            color: 'var(--text-muted)', 
            letterSpacing: '0.15em', 
            marginBottom: '8px',
            textTransform: 'uppercase',
          }}>
            Resolving
          </div>
          <div style={{ 
            fontSize: '16px', 
            color: 'var(--accent-cyan)', 
            fontWeight: 'bold',
            textTransform: 'uppercase',
          }}>
            {region.name}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Engine processing turn...
          </div>
        </div>
      )}

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="region-detail-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ 
            fontSize: '18px', 
            fontWeight: 'bold', 
            color: 'var(--text-primary)', 
            letterSpacing: '0.08em', 
            margin: 0,
            textTransform: 'uppercase',
          }}>
            {region.name}
          </h2>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '6px 0 0' }}>
            {region.terrain.join(' / ').toUpperCase()}
          </p>
        </div>
        <button onClick={handleClose} style={{
          background: 'transparent', 
          border: '1px solid var(--border-primary)', 
          borderRadius: '6px',
          color: 'var(--text-muted)', 
          padding: '6px 12px', 
          cursor: 'pointer', 
          fontSize: '11px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          transition: 'all 0.15s ease',
        }}>
          Close
        </button>
      </div>

      {/* ── Faction + Connectivity ─────────────────────────────────── */}
      {faction && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
          <div className="faction-badge" style={{ color: faction.color }}>
            <span className="faction-badge-dot" style={{ background: faction.color }} />
            <span>{faction.name}</span>
          </div>
          <span className="connectivity-badge" style={{
            color: connectivityColor(region.connectivity),
            border: `1px solid ${connectivityColor(region.connectivity)}`,
            background: `${connectivityColor(region.connectivity)}15`,
          }}>
            {region.connectivity}
          </span>
        </div>
      )}

      {/* ── Description ────────────────────────────────────────────── */}
      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '16px' }}>
        {region.description}
      </p>

      {/* ── Content summary ────────────────────────────────────────── */}
      {(content.npcs.length > 0 || content.jobs.length > 0 || content.threads.length > 0) && (
        <div style={{ 
          marginBottom: '16px', 
          padding: '12px', 
          background: 'rgba(18, 18, 18, 0.5)', 
          borderRadius: '8px',
          border: '1px solid var(--border-secondary)',
        }}>
          {content.npcs.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-purple)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>👤</span>
              <span>{content.npcs.join(', ')}</span>
            </div>
          )}
          {content.jobs.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-green)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>💼</span>
              <span>{content.jobs.join(', ')}</span>
            </div>
          )}
          {content.threads.length > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>⚡</span>
              <span>{content.threads.join(', ')}</span>
            </div>
          )}
        </div>
      )}

      {/* ── Current region badge ───────────────────────────────────── */}
      {isCurrentRegion && (
        <div style={{ 
          borderTop: '1px solid var(--border-primary)', 
          paddingTop: '16px', 
          fontSize: '12px', 
          color: 'var(--accent-cyan)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span style={{ 
            width: '8px', 
            height: '8px', 
            borderRadius: '50%', 
            background: 'var(--accent-cyan)',
            boxShadow: '0 0 8px var(--accent-cyan)',
          }} />
          <span style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'bold' }}>
            You Are Here
          </span>
        </div>
      )}

      {/* ── Travel assessment (non-current regions only) ───────────── */}
      {!isCurrentRegion && (
        <div style={{ borderTop: '1px solid var(--border-primary)', paddingTop: '16px' }}>
          <div className="section-divider" style={{ marginTop: 0 }}>
            Travel Assessment
          </div>

          {proposalLoading && (
            <div style={{ 
              fontSize: '12px', 
              color: 'var(--text-muted)', 
              padding: '16px 0',
              textAlign: 'center',
            }}>
              <div style={{ 
                width: '20px', 
                height: '20px', 
                border: '2px solid var(--bg-tertiary)',
                borderTopColor: 'var(--accent-steel)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 12px',
              }} />
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
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '16px 0', textAlign: 'center' }}>
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
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: '1.5' }}>
        {proposal.summary}
      </div>

      {/* Requirements with met/unmet/bypassable status */}
      {proposal.requirements.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ 
            fontSize: '10px', 
            color: 'var(--text-muted)', 
            marginBottom: '8px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>Requirements</div>
          {proposal.requirements.map((req, idx) => (
            <div key={idx} style={{
              fontSize: '12px', 
              marginBottom: '4px', 
              padding: '8px 12px',
              background: 'rgba(0, 0, 0, 0.2)',
              borderRadius: '4px',
              borderLeft: `2px solid ${
                req.status === 'met' ? 'var(--accent-green)' :
                req.status === 'bypassable' ? 'var(--accent-amber)' : 'var(--accent-red)'
              }`,
              color: req.status === 'met' ? 'var(--accent-green)' :
                     req.status === 'bypassable' ? 'var(--accent-amber)' : 'var(--accent-red)',
            }}>
              <span style={{ marginRight: '6px' }}>
                {req.status === 'met' ? '✓' : req.status === 'bypassable' ? '◈' : '✗'}
              </span>
              {req.label}
              {req.detail && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '8px' }}>— {req.detail}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Cost preview from engine */}
      <CostPreview costs={proposal.costs} />

      {/* Risks with severity */}
      {proposal.risks.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ 
            fontSize: '10px', 
            color: 'var(--text-muted)', 
            marginBottom: '8px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>Risks</div>
          {proposal.risks.map((risk, idx) => (
            <div key={idx} style={{
              fontSize: '12px', 
              marginBottom: '4px', 
              padding: '8px 12px',
              background: 'rgba(0, 0, 0, 0.2)',
              borderRadius: '4px',
              borderLeft: `2px solid ${
                risk.severity === 'high' ? 'var(--accent-red)' :
                risk.severity === 'medium' ? 'var(--accent-amber)' : 'var(--text-secondary)'
              }`,
              color: risk.severity === 'high' ? 'var(--accent-red)' :
                     risk.severity === 'medium' ? 'var(--accent-amber)' : 'var(--text-secondary)',
            }}>
              <span style={{ marginRight: '6px' }}>
                {risk.severity === 'high' ? '▲' : risk.severity === 'medium' ? '◆' : '◇'}
              </span>
              {risk.label}
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '8px' }}>— {risk.detail}</span>
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
          type="direct"
        />
      )}

      {/* Blocked indicator + alternatives */}
      {!proposal.feasible && proposal.alternatives.length > 0 && (
        <div style={{ 
          fontSize: '11px', 
          color: 'var(--accent-red)', 
          marginBottom: '12px',
          padding: '10px',
          background: 'rgba(248, 81, 73, 0.1)',
          borderRadius: '6px',
          borderLeft: '2px solid var(--accent-red)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          Direct Route Blocked
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
          type="alternative"
        />
      ))}

      {/* Completely blocked — no alternatives either */}
      {!proposal.feasible && proposal.alternatives.length === 0 && (
        <div style={{
          fontSize: '12px', 
          color: 'var(--accent-red)', 
          marginTop: '12px', 
          padding: '16px',
          background: 'rgba(248, 81, 73, 0.1)', 
          borderRadius: '8px',
          border: '1px solid var(--accent-red)',
          textAlign: 'center',
        }}>
          No viable route from current location.
        </div>
      )}
    </>
  );
}

/** Displays the engine's cost preview — turns, fuel, condition, social energy, credits, standing */
function CostPreview({ costs }: { costs: TravelProposal['costs'] }) {
  const items: Array<{ label: string; value: string; color: string; icon: string }> = [];

  if (costs.turns > 0)
    items.push({ label: 'Turns', value: String(costs.turns), color: 'var(--text-secondary)', icon: '⏱' });
  if (costs.fuel > 0)
    items.push({ label: 'Fuel', value: `-${costs.fuel}`, color: 'var(--accent-amber)', icon: '⛽' });
  if (costs.condition > 0)
    items.push({ label: 'Condition', value: `-${costs.condition}`, color: 'var(--accent-amber)', icon: '🔧' });
  if (costs.social_energy > 0)
    items.push({ label: 'Social Energy', value: `-${costs.social_energy}`, color: 'var(--accent-amber)', icon: '💬' });
  if (costs.credits > 0)
    items.push({ label: 'Credits', value: `-${costs.credits}`, color: 'var(--accent-amber)', icon: '💳' });

  for (const [factionId, delta] of Object.entries(costs.standing_changes)) {
    if (delta !== 0) {
      const sign = delta > 0 ? '+' : '';
      items.push({
        label: factionId.replace(/_/g, ' '),
        value: `${sign}${delta}`,
        color: delta > 0 ? 'var(--accent-green)' : 'var(--accent-red)',
        icon: delta > 0 ? '↑' : '↓',
      });
    }
  }

  if (items.length === 0) return null;

  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ 
        fontSize: '10px', 
        color: 'var(--text-muted)', 
        marginBottom: '8px',
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
      }}>Costs</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {items.map((item, idx) => (
          <div key={idx} style={{
            fontSize: '12px', 
            padding: '8px 12px',
            background: 'rgba(0, 0, 0, 0.2)',
            borderRadius: '4px',
            borderLeft: `2px solid ${item.color}`,
            color: item.color,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span><span style={{ marginRight: '8px' }}>{item.icon}</span>{item.label}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}>{item.value}</span>
          </div>
        ))}
      </div>
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
  const items: Array<{ text: string; danger: boolean; icon: string }> = [];

  const turns = proposal.costs.turns || 1;
  items.push({ text: `Consume ${turns} turn${turns > 1 ? 's' : ''}`, danger: false, icon: '⏱' });

  if (proposal.costs.fuel > 0)
    items.push({ text: `Use ${proposal.costs.fuel} fuel`, danger: false, icon: '⛽' });
  if (proposal.costs.condition > 0)
    items.push({ text: `Wear ${proposal.costs.condition} condition`, danger: false, icon: '🔧' });

  // Alternative costs override base costs for social/credits
  if (alternative) {
    if (alternative.costs.social_energy > 0)
      items.push({ text: `Drain ${alternative.costs.social_energy} social energy`, danger: false, icon: '💬' });
    if (alternative.costs.credits > 0)
      items.push({ text: `Spend ${alternative.costs.credits} credits`, danger: false, icon: '💳' });
    if (alternative.consequence)
      items.push({ text: `Risk: ${alternative.consequence.replace(/_/g, ' ')}`, danger: true, icon: '⚠' });
  } else {
    if (proposal.costs.social_energy > 0)
      items.push({ text: `Drain ${proposal.costs.social_energy} social energy`, danger: false, icon: '💬' });
    if (proposal.costs.credits > 0)
      items.push({ text: `Spend ${proposal.costs.credits} credits`, danger: false, icon: '💳' });
  }

  // Standing changes
  for (const [factionId, delta] of Object.entries(proposal.costs.standing_changes)) {
    if (delta !== 0) {
      const label = factionId.replace(/_/g, ' ');
      const sign = delta > 0 ? '+' : '';
      items.push({ text: `${label} standing ${sign}${delta}`, danger: delta < 0, icon: delta > 0 ? '↑' : '↓' });
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {items.map((item, idx) => (
        <div key={idx} style={{
          fontSize: '12px',
          color: item.danger ? 'var(--accent-red)' : 'var(--accent-amber)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{item.icon}</span>
          <span>{item.text}</span>
        </div>
      ))}
    </div>
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
  type,
}: {
  label: string;
  description: string;
  cost?: { turns?: number; social_energy?: number; credits?: number };
  consequence?: string | null;
  available: boolean;
  onSelect: () => void;
  type: 'direct' | 'alternative';
}) {
  const costParts = cost
    ? [
        cost.turns && cost.turns > 0 ? `${cost.turns} turn${cost.turns > 1 ? 's' : ''}` : null,
        cost.social_energy && cost.social_energy > 0 ? `${cost.social_energy} SE` : null,
        cost.credits && cost.credits > 0 ? `${cost.credits}c` : null,
      ].filter(Boolean)
    : [];

  return (
    <div className="travel-option-card" style={{
      opacity: available ? 1 : 0.5,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ 
            fontSize: '12px', 
            fontWeight: 'bold', 
            color: available ? 'var(--text-primary)' : 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
          }}>
            {type === 'direct' && <span style={{ color: 'var(--accent-green)', marginRight: '6px' }}>●</span>}
            {label}
          </span>
        </div>
        {available && (
          <button onClick={onSelect} style={{
            fontSize: '10px', 
            padding: '6px 14px', 
            background: type === 'direct' ? 'var(--accent-green)' : 'var(--accent-steel)',
            color: type === 'direct' ? 'black' : 'black',
            border: 'none', 
            borderRadius: '4px', 
            cursor: 'pointer', 
            fontWeight: 'bold',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            transition: 'all 0.15s ease',
            boxShadow: type === 'direct' ? '0 2px 8px rgba(126, 231, 135, 0.3)' : '0 2px 8px rgba(121, 192, 255, 0.3)',
          }}>
            Select
          </button>
        )}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
        {description}
      </div>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {costParts.length > 0 && (
          <span style={{ 
            fontSize: '10px', 
            color: 'var(--accent-amber)', 
            padding: '3px 8px',
            background: 'rgba(255, 166, 87, 0.1)',
            borderRadius: '3px',
          }}>
            {costParts.join(' · ')}
          </span>
        )}
        {consequence && (
          <span style={{ 
            fontSize: '10px', 
            color: 'var(--accent-red)', 
            padding: '3px 8px',
            background: 'rgba(248, 81, 73, 0.1)',
            borderRadius: '3px',
          }}>
            Risk: {consequence.replace(/_/g, ' ')}
          </span>
        )}
      </div>
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
