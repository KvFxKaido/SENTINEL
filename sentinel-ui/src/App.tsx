import { useState } from 'react';
import './index.css';
import { Sidebar } from './components/Sidebar';
import { MainPanel } from './components/MainPanel';
import { CommandInput } from './components/CommandInput';
import { CodecBox } from './components/CodecBox';
import type { GameState, Message } from './types';

// Mock initial state for development
const mockState: GameState = {
  campaign: {
    name: 'Operation Ghost Protocol',
    session: 3,
    phase: 'execution',
  },
  character: {
    name: 'CIPHER',
    background: 'Intel Operative',
    socialEnergy: 68,
  },
  factions: {
    nexus: 'neutral',
    ember_colonies: 'friendly',
    lattice: 'unfriendly',
    ghost_networks: 'neutral',
  },
  activeNpc: null,
  loadout: ['Surveillance Kit', 'Encrypted Comm', 'Trauma Kit'],
};

function App() {
  const [gameState, setGameState] = useState<GameState>(mockState);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'narrative',
      content: 'The checkpoint looms ahead. Two guards in Nexus uniforms scan the sparse crowd with the practiced boredom of routine duty. Your Ember contact mentioned a supply truck at 0300 — that\'s twenty minutes from now.',
      timestamp: new Date(),
    },
    {
      id: '2',
      type: 'choice',
      content: 'How do you approach?',
      options: [
        'Blend into the crowd, wait for the truck',
        'Approach the guards directly, flash credentials',
        'Find another way around',
        'Something else...',
      ],
      timestamp: new Date(),
    },
  ]);
  const [showCodec, setShowCodec] = useState(false);

  const handleCommand = (input: string) => {
    // Add player message
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      type: 'player',
      content: input,
      timestamp: new Date(),
    }]);

    // Mock response (will be replaced with WebSocket)
    if (input.startsWith('/')) {
      // Handle command
      if (input === '/status') {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: 'system',
          content: `Campaign: ${gameState.campaign.name}\nSession: ${gameState.campaign.session}\nPhase: ${gameState.campaign.phase}`,
          timestamp: new Date(),
        }]);
      }
    } else if (input === '2') {
      // Simulate NPC response
      setShowCodec(true);
      setGameState(prev => ({
        ...prev,
        activeNpc: {
          name: 'CHECKPOINT GUARD',
          faction: 'nexus',
          disposition: 'wary',
          portrait: null,
        },
      }));
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-sentinel-bg overflow-hidden">
      {/* Top bar */}
      <header className="h-10 bg-sentinel-surface border-b border-sentinel-border flex items-center px-4 justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sentinel-accent font-bold tracking-wider">SENTINEL</span>
          <span className="text-sentinel-dim text-sm">v0.1.0</span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-sentinel-secondary">{gameState.campaign.name}</span>
          <span className="text-sentinel-dim">Session {gameState.campaign.session}</span>
          <span className="text-sentinel-warning uppercase">{gameState.campaign.phase}</span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar gameState={gameState} />

        {/* Main panel */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <MainPanel messages={messages} />
          <CommandInput onSubmit={handleCommand} />
        </main>
      </div>

      {/* Codec overlay */}
      {showCodec && gameState.activeNpc && (
        <CodecBox
          npc={gameState.activeNpc}
          dialogue="Papers. Now."
          onClose={() => setShowCodec(false)}
        />
      )}
    </div>
  );
}

export default App;
