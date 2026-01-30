import { useState, useEffect } from 'react';
import { tutorialManager, type TutorialState } from './tutorial';

export function useTutorial() {
  const [state, setState] = useState<TutorialState>(tutorialManager.getState());

  useEffect(() => {
    const unsub = tutorialManager.subscribe(setState);
    return () => { unsub(); };
  }, []);

  return {
    state,
    onMove: () => tutorialManager.onMove(),
    onApproach: (dist: number) => tutorialManager.onApproachObject(dist),
    onInteract: () => tutorialManager.onInteract(),
    getHint: (type: 'movement' | 'approach' | 'interaction') => tutorialManager.getHint(type),
  };
}
