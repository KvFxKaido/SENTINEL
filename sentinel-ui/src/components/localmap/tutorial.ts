/**
 * Tutorial System for SENTINEL 2D
 * 
 * Teaches through observation and subtle cues, not modal instructions.
 * Persists progress to localStorage.
 */

import type { Point } from './types';

export type TutorialStep = 
  | 'movement'     // 0: Learn to move
  | 'approach'     // 1: Learn that proximity triggers hints
  | 'hesitation'   // 2: Learn that lingering reveals info (optional)
  | 'interaction'  // 3: Learn to use E
  | 'complete';    // 4: Done

export interface TutorialState {
  step: TutorialStep;
  hasMoved: boolean;
  hasApproached: boolean;
  hasInteracted: boolean;
  hintsShown: Set<string>;
}

const STORAGE_KEY = 'sentinel_tutorial_v1';

class TutorialManager {
  private state: TutorialState;
  private listeners: Set<(state: TutorialState) => void> = new Set();

  constructor() {
    this.state = this.loadState();
  }

  private loadState(): TutorialState {
    if (typeof localStorage === 'undefined') {
      return this.defaultState();
    }
    
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          ...parsed,
          hintsShown: new Set(parsed.hintsShown),
        };
      }
    } catch (e) {
      console.warn('Failed to load tutorial state', e);
    }
    
    return this.defaultState();
  }

  private defaultState(): TutorialState {
    return {
      step: 'movement',
      hasMoved: false,
      hasApproached: false,
      hasInteracted: false,
      hintsShown: new Set(),
    };
  }

  private saveState() {
    if (typeof localStorage === 'undefined') return;
    
    try {
      const serialized = {
        ...this.state,
        hintsShown: Array.from(this.state.hintsShown),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(serialized));
    } catch (e) {
      console.warn('Failed to save tutorial state', e);
    }
    
    this.notify();
  }

  public subscribe(listener: (state: TutorialState) => void) {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach(l => l(this.state));
  }

  public getState() {
    return this.state;
  }

  public reset() {
    this.state = this.defaultState();
    this.saveState();
  }

  // ==========================================================================
  // Triggers
  // ==========================================================================

  public onMove() {
    if (this.state.step === 'movement' && !this.state.hasMoved) {
      // Don't advance immediately, let them move a bit
      this.state.hasMoved = true;
      this.saveState();
    }
  }

  public onApproachObject(dist: number) {
    if (this.state.step === 'movement' && this.state.hasMoved) {
      this.state.step = 'approach';
      this.saveState();
    }
    
    if (this.state.step === 'approach' && !this.state.hasApproached) {
      this.state.hasApproached = true;
      // Advance to interaction immediately upon approach
      this.state.step = 'interaction';
      this.saveState();
    }
  }

  public onInteract() {
    if (this.state.step === 'interaction' && !this.state.hasInteracted) {
      this.state.hasInteracted = true;
      this.state.step = 'complete';
      this.saveState();
    }
  }

  public getHint(type: 'movement' | 'approach' | 'interaction'): string | null {
    if (this.state.step === 'complete') return null;

    switch (type) {
      case 'movement':
        if (this.state.step === 'movement' && !this.state.hasMoved) {
          // Only show after a delay? handled by UI
          return 'WASD to move';
        }
        break;
      case 'approach':
        if (this.state.step === 'approach') {
          return 'Move closer to investigate';
        }
        break;
      case 'interaction':
        if (this.state.step === 'interaction') {
          return 'E to interact';
        }
        break;
    }
    return null;
  }
}

export const tutorialManager = new TutorialManager();
