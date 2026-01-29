/**
 * Overworld Components
 * 
 * The overworld makes distance, exposure, and hesitation legible.
 * Movement is free but non-authoritative — proximity alone never commits.
 * 
 * Phase 4 adds:
 * - Multi-region transitions
 * - Faction pressure visualization
 * - Combat integration
 */

// Core components
export { OverworldView } from './OverworldView';
export { OverworldCanvas } from './OverworldCanvas';
export { InteractionPanel } from './InteractionPanel';

// Phase 4: Region transitions
export { RegionTransition, MiniMap } from './RegionTransition';

// Phase 4: Faction pressure
export { 
  FactionLegend, 
  FactionIndicator,
  drawFactionPressure,
  generateFactionZones,
} from './FactionPressure';

// Phase 4: Combat
export { 
  CombatOverlay,
  createInitialCombatState,
  processCombatAction,
} from './CombatOverlay';

// Types
export * from './types';
export * from './expansion-types';
