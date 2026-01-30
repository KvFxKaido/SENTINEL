import { useEffect, useMemo, useState } from 'react';
import type { DialogueOption, DialogueResponse, SocialEnergyState } from '../../lib/gameApi';
import './dialogue.css';

interface DialogueOverlayProps {
  active: boolean;
  npcName: string;
  npcFaction: string | null;
  npcDisposition: string;
  response: DialogueResponse | null;
  socialEnergy: SocialEnergyState | null;
  loading: boolean;
  error?: string | null;
  onSelectOption: (option: DialogueOption) => void;
  onExit: () => void;
}

export function DialogueOverlay({
  active,
  npcName,
  npcFaction,
  npcDisposition,
  response,
  socialEnergy,
  loading,
  error,
  onSelectOption,
  onExit,
}: DialogueOverlayProps) {
  const dialogueText = response?.dialogue_text || (loading ? 'Establishing contact...' : '...');
  const endedByNpc = response?.ended_by_npc === true;
  const responseError = response?.error || error || null;

  const [typedText, setTypedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (!dialogueText) {
      setTypedText('');
      return;
    }

    let index = 0;
    setTypedText('');
    setIsTyping(true);

    const timer = window.setInterval(() => {
      index += 1;
      setTypedText(dialogueText.slice(0, index));
      if (index >= dialogueText.length) {
        clearInterval(timer);
        setIsTyping(false);
      }
    }, 30);

    return () => {
      clearInterval(timer);
      setIsTyping(false);
    };
  }, [dialogueText]);

  useEffect(() => {
    if (!endedByNpc) return;
    const timer = window.setTimeout(() => {
      onExit();
    }, 2000);
    return () => clearTimeout(timer);
  }, [endedByNpc, onExit]);

  const energyPercent = useMemo(() => {
    if (!socialEnergy) return null;
    if (typeof socialEnergy.percentage === 'number') {
      return Math.max(0, Math.min(100, socialEnergy.percentage));
    }
    if (socialEnergy.max <= 0) return 0;
    return Math.max(0, Math.min(100, (socialEnergy.current / socialEnergy.max) * 100));
  }, [socialEnergy]);

  const energyClass = useMemo(() => {
    if (energyPercent === null) return 'energy-unknown';
    if (energyPercent > 66) return 'energy-high';
    if (energyPercent > 33) return 'energy-mid';
    return 'energy-low';
  }, [energyPercent]);

  return (
    <div className={`dialogue-overlay ${active ? 'active' : ''}`}>
      <div className="dialogue-header">
        <div className="dialogue-npc">
          <div className="dialogue-npc-name">{npcName}</div>
          <div className="dialogue-badges">
            {npcFaction && (
              <span className="dialogue-faction">
                {npcFaction.replace(/_/g, ' ')}
              </span>
            )}
            <span className={`dialogue-disposition disposition-${npcDisposition || 'neutral'}`}>
              {npcDisposition || 'neutral'}
            </span>
          </div>
        </div>
        <button className="dialogue-exit" onClick={onExit}>
          Exit
        </button>
      </div>

      <div className="dialogue-body">
        <div className="dialogue-text">
          <p>{typedText}</p>
          {isTyping && <span className="dialogue-cursor">|</span>}
        </div>

        {endedByNpc && (
          <div className="dialogue-ended">NPC walks away.</div>
        )}

        {responseError && (
          <div className="dialogue-error">Connection lost.</div>
        )}

        {response?.memory_tags && response.memory_tags.length > 0 && (
          <div className="dialogue-memory">
            <span>Memory:</span>
            {response.memory_tags.map(tag => (
              <span key={tag} className="dialogue-memory-tag">{tag}</span>
            ))}
          </div>
        )}
      </div>

      <div className="dialogue-footer">
        <div className="dialogue-energy">
          <div className="energy-label">Social Energy</div>
          <div className="energy-bar">
            <div
              className={`energy-fill ${energyClass}`}
              style={{ width: `${energyPercent ?? 0}%` }}
            />
          </div>
          <div className="energy-values">
            {socialEnergy
              ? `${socialEnergy.current}/${socialEnergy.max}`
              : 'Unknown'}
          </div>
        </div>

        <div className="dialogue-options">
          {response?.options?.length ? (
            response.options.map(option => (
              <button
                key={option.id}
                className={`dialogue-option tone-${option.tone || 'neutral'}`}
                onClick={() => onSelectOption(option)}
                disabled={loading || endedByNpc}
              >
                <span className="option-text">{option.text}</span>
                <span className="option-cost">
                  {option.social_cost > 0 ? `-${option.social_cost}` : '0'}
                </span>
                {option.risk_hint && (
                  <span className="option-risk">{option.risk_hint}</span>
                )}
              </button>
            ))
          ) : loading ? (
            <div className="dialogue-empty">Awaiting response...</div>
          ) : (
            <div className="dialogue-empty">No response offered.</div>
          )}
        </div>
      </div>
    </div>
  );
}
