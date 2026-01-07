import './index.css';
import { Sidebar } from './components/Sidebar';
import { MainPanel } from './components/MainPanel';
import { CommandInput } from './components/CommandInput';
import { CodecBox } from './components/CodecBox';
import { useGameSocket } from './hooks/useGameSocket';
import type { GameState } from './types';

// Fallback state when not connected
const fallbackState: GameState = {
  campaign: {
    name: 'Not Connected',
    session: 0,
    phase: 'briefing',
  },
  character: {
    name: 'UNKNOWN',
    background: 'Unknown',
    socialEnergy: 100,
  },
  factions: {},
  activeNpc: null,
  loadout: [],
};

function App() {
  const {
    connected,
    gameState,
    messages,
    codecNpc,
    sendCommand,
    sendInput,
    closeCodec,
  } = useGameSocket();

  const state = gameState || fallbackState;

  const handleSubmit = (input: string) => {
    if (input.startsWith('/')) {
      sendCommand(input);
    } else {
      sendInput(input);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-sentinel-bg overflow-hidden">
      {/* Top bar */}
      <header className="h-10 bg-sentinel-surface border-b border-sentinel-border flex items-center px-4 justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sentinel-accent font-bold tracking-wider">SENTINEL</span>
          <span className="text-sentinel-dim text-sm">v0.1.0</span>
          {/* Connection indicator */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-sentinel-danger animate-pulse'}`} />
            <span className={`text-xs ${connected ? 'text-green-500' : 'text-sentinel-danger'}`}>
              {connected ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-sentinel-secondary">{state.campaign.name}</span>
          <span className="text-sentinel-dim">Session {state.campaign.session}</span>
          <span className="text-sentinel-warning uppercase">{state.campaign.phase}</span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar gameState={state} />

        {/* Main panel */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <MainPanel messages={messages} />
          <CommandInput onSubmit={handleSubmit} disabled={!connected} />
        </main>
      </div>

      {/* Codec overlay */}
      {codecNpc && (
        <CodecBox
          npc={codecNpc.npc}
          dialogue={codecNpc.dialogue}
          onClose={closeCodec}
        />
      )}

      {/* Offline overlay */}
      {!connected && (
        <div className="fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-sentinel-surface border border-sentinel-danger px-4 py-2 rounded shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-sentinel-danger animate-pulse" />
            <span className="text-sentinel-secondary text-sm">
              Connecting to SENTINEL server...
            </span>
          </div>
          <p className="text-sentinel-dim text-xs mt-1">
            Start the server: <code className="text-sentinel-accent">python -m src.interface.websocket_server</code>
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
