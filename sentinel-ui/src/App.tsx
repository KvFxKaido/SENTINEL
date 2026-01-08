import './index.css';
import { Sidebar } from './components/Sidebar';
import { MainPanel } from './components/MainPanel';
import { CommandInput } from './components/CommandInput';
import { CodecBox } from './components/CodecBox';
import type { GameState } from './types';

// Placeholder state for UI development
const placeholderState: GameState = {
  campaign: {
    name: 'SENTINEL',
    session: 0,
    phase: 'briefing',
  },
  character: {
    name: 'OPERATIVE',
    background: 'Unknown',
    socialEnergy: 100,
  },
  factions: {},
  activeNpc: null,
  loadout: [],
};

function App() {
  const handleSubmit = (input: string) => {
    console.log('Input:', input);
    // TODO: Connect to game engine
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
          <span className="text-sentinel-secondary">{placeholderState.campaign.name}</span>
          <span className="text-sentinel-dim">Session {placeholderState.campaign.session}</span>
          <span className="text-sentinel-warning uppercase">{placeholderState.campaign.phase}</span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar gameState={placeholderState} />

        {/* Main panel */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <MainPanel messages={[]} />
          <CommandInput onSubmit={handleSubmit} disabled={false} />
        </main>
      </div>
    </div>
  );
}

export default App;
