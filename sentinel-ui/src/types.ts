// Game state types

export type Disposition = 'hostile' | 'wary' | 'neutral' | 'warm' | 'loyal';
export type MissionPhase = 'briefing' | 'planning' | 'execution' | 'resolution' | 'debrief';

export interface NPC {
  name: string;
  faction: string;
  disposition: Disposition;
  portrait: string | null;
  role?: string;
}

export interface GameState {
  campaign: {
    name: string;
    session: number;
    phase: MissionPhase;
  };
  character: {
    name: string;
    background: string;
    socialEnergy: number;
  };
  factions: Record<string, Disposition>;
  activeNpc: NPC | null;
  loadout: string[];
}

export type MessageType = 'narrative' | 'choice' | 'player' | 'system' | 'npc';

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  options?: string[];
  npc?: NPC;
}
