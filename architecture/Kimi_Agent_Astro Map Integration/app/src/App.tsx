import { useState } from 'react';
import { WorldMap } from '@/components/map';
import type { Region, RegionConnectivity, ContentMarker } from '@/types/map';
import { regions } from '@/data/regions';
import { Button } from '@/components/ui/button';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription 
} from '@/components/ui/dialog';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Demo state - simulating different campaign states
const demoStates = {
  'new_campaign': {
    regionStates: Object.fromEntries(
      Object.keys(regions).map(r => [r, 'disconnected'])
    ) as Record<Region, RegionConnectivity>,
    currentRegion: 'rust_corridor' as Region,
    markers: {} as Record<Region, ContentMarker[]>,
  },
  'early_game': {
    regionStates: {
      rust_corridor: 'embedded',
      breadbasket: 'connected',
      northern_reaches: 'aware',
      pacific_corridor: 'aware',
    } as Record<Region, RegionConnectivity>,
    currentRegion: 'rust_corridor' as Region,
    markers: {
      rust_corridor: [{ type: 'current' }, { type: 'npc', count: 2 }, { type: 'job' }],
      breadbasket: [{ type: 'npc', count: 1 }],
    } as Record<Region, ContentMarker[]>,
  },
  'mid_game': {
    regionStates: {
      rust_corridor: 'embedded',
      breadbasket: 'embedded',
      northern_reaches: 'connected',
      pacific_corridor: 'connected',
      appalachian_hollows: 'aware',
      texas_spine: 'aware',
    } as Record<Region, RegionConnectivity>,
    currentRegion: 'breadbasket' as Region,
    markers: {
      rust_corridor: [{ type: 'npc', count: 3 }],
      breadbasket: [{ type: 'current' }, { type: 'thread' }],
      northern_reaches: [{ type: 'job' }],
      pacific_corridor: [{ type: 'npc', count: 1 }],
    } as Record<Region, ContentMarker[]>,
  },
  'late_game': {
    regionStates: Object.fromEntries(
      Object.keys(regions).map(r => [r, 'embedded'])
    ) as Record<Region, RegionConnectivity>,
    currentRegion: 'gulf_passage' as Region,
    markers: {
      gulf_passage: [{ type: 'current' }, { type: 'job' }, { type: 'thread' }],
      sovereign_south: [{ type: 'npc', count: 2 }],
      desert_sprawl: [{ type: 'npc', count: 1 }],
    } as Record<Region, ContentMarker[]>,
  },
};

function App() {
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [demoState, setDemoState] = useState<keyof typeof demoStates>('mid_game');
  const [showInfo, setShowInfo] = useState(true);

  const currentState = demoStates[demoState];

  // Fill in missing regions with disconnected state
  const fullRegionStates: Record<Region, RegionConnectivity> = {
    ...Object.fromEntries(
      Object.keys(regions).map(r => [r, 'disconnected'])
    ) as Record<Region, RegionConnectivity>,
    ...currentState.regionStates,
  };

  const handleRegionClick = (region: Region) => {
    setSelectedRegion(region);
  };

  return (
    <div className="min-h-screen bg-black text-[var(--text-primary)]">
      {/* Header */}
      <header className="border-b border-[var(--border-primary)] bg-[var(--bg-secondary)]">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold tracking-wider terminal-text text-[var(--accent-steel)]">
              SENTINEL
            </h1>
            <span className="text-xs text-[var(--text-muted)]">
              WORLD MAP VISUALIZATION
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Demo state selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--text-muted)]">CAMPAIGN STATE:</span>
              <Select value={demoState} onValueChange={(v) => setDemoState(v as keyof typeof demoStates)}>
                <SelectTrigger className="w-[140px] h-8 text-xs bg-[var(--bg-primary)] border-[var(--border-primary)]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[var(--bg-secondary)] border-[var(--border-primary)]">
                  <SelectItem value="new_campaign" className="text-xs">New Campaign</SelectItem>
                  <SelectItem value="early_game" className="text-xs">Early Game</SelectItem>
                  <SelectItem value="mid_game" className="text-xs">Mid Game</SelectItem>
                  <SelectItem value="late_game" className="text-xs">Late Game</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowInfo(!showInfo)}
              className="text-xs border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]"
            >
              {showInfo ? 'Hide Info' : 'Show Info'}
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex">
        {/* Map area */}
        <div className="flex-1 relative" style={{ height: 'calc(100vh - 57px)' }}>
          <WorldMap
            currentRegion={currentState.currentRegion}
            regionStates={fullRegionStates}
            markers={currentState.markers}
            onRegionClick={handleRegionClick}
            showLegend={true}
          />
        </div>

        {/* Info sidebar */}
        {showInfo && (
          <div className="w-80 border-l border-[var(--border-primary)] bg-[var(--bg-secondary)] p-4 overflow-y-auto"
               style={{ height: 'calc(100vh - 57px)' }}>
            <Tabs defaultValue="about" className="w-full">
              <TabsList className="w-full bg-[var(--bg-primary)]">
                <TabsTrigger value="about" className="flex-1 text-xs">About</TabsTrigger>
                <TabsTrigger value="factions" className="flex-1 text-xs">Factions</TabsTrigger>
                <TabsTrigger value="mechanics" className="flex-1 text-xs">Mechanics</TabsTrigger>
              </TabsList>

              <TabsContent value="about" className="mt-4 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-[var(--accent-steel)] mb-2">
                    NETWORK MAP SYSTEM
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    A Metroid-inspired interactive map that visualizes regions, social connectivity, 
                    and narrative anchoring in the post-collapse world of SENTINEL.
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-[var(--text-muted)]">KEY PRINCIPLES</h4>
                  <ul className="text-xs text-[var(--text-secondary)] space-y-1.5">
                    <li className="flex gap-2">
                      <span className="text-[var(--accent-cyan)]">•</span>
                      <span>Fog represents <strong>social disconnection</strong>, not geographic ignorance</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[var(--accent-cyan)]">•</span>
                      <span>Gates are <strong>negotiable</strong>, not binary — multiple solutions exist</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[var(--accent-cyan)]">•</span>
                      <span><strong>Relationships over keycards</strong> — the map visualizes social reach</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[var(--accent-cyan)]">•</span>
                      <span><strong>Risk over locks</strong> — blocked routes can still be traversed at cost</span>
                    </li>
                  </ul>
                </div>

                <div className="p-3 border border-[var(--border-primary)] rounded bg-[var(--bg-primary)]">
                  <p className="text-xs text-[var(--text-muted)] italic">
                    &ldquo;The world is stable the way a cracked dam is stable.&rdquo;
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    — SENTINEL Canon Bible
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="factions" className="mt-4 space-y-3">
                <p className="text-xs text-[var(--text-secondary)] mb-3">
                  Eleven factions compete for influence in post-collapse North America. 
                  Each is right about something and dangerously wrong when taken too far.
                </p>
                
                {Object.values(regions).map((region) => (
                  <div 
                    key={region.id} 
                    className="p-2 border border-[var(--border-secondary)] rounded hover:border-[var(--border-primary)] transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: 
                          {nexus: '#a855f7', ember_colonies: '#f97316', lattice: '#3b82f6', 
                           convergence: '#06b6d4', covenant: '#eab308', wanderers: '#22c55e',
                           cultivators: '#10b981', steel_syndicate: '#ef4444', witnesses: '#f59e0b',
                           architects: '#6366f1', ghost_networks: '#6b7280'}[region.primaryFaction] || '#6b7280'
                        }}
                      />
                      <span className="text-xs font-medium">{region.name}</span>
                    </div>
                    <p className="text-[10px] text-[var(--text-muted)] mt-1 ml-4">
                      {region.primaryFaction?.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </p>
                  </div>
                ))}
              </TabsContent>

              <TabsContent value="mechanics" className="mt-4 space-y-4">
                <div>
                  <h4 className="text-xs font-bold text-[var(--accent-steel)] mb-2">
                    CONNECTIVITY STATES
                  </h4>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2">
                      <span className="text-[var(--state-disconnected)] font-mono">░░░</span>
                      <div>
                        <span className="text-xs font-medium">DISCONNECTED</span>
                        <p className="text-[10px] text-[var(--text-muted)]">
                          No contacts, no intel, no reason to go
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-[var(--state-aware)] font-mono">▒▒▒</span>
                      <div>
                        <span className="text-xs font-medium">AWARE</span>
                        <p className="text-[10px] text-[var(--text-muted)]">
                          Someone mentioned it; you have a thread to pull
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-[var(--state-connected)] font-mono">⬡</span>
                      <div>
                        <span className="text-xs font-medium">CONNECTED</span>
                        <p className="text-[10px] text-[var(--text-muted)]">
                          You&apos;ve been there or have reliable contacts
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-[var(--state-embedded)] font-mono">⬢</span>
                      <div>
                        <span className="text-xs font-medium">EMBEDDED</span>
                        <p className="text-[10px] text-[var(--text-muted)]">
                          Deep network — multiple NPCs, resolved threads
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-bold text-[var(--accent-steel)] mb-2">
                    GATE TYPES
                  </h4>
                  <div className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                    <p><strong className="text-[var(--text-primary)]">Terrain:</strong> Difficult geography</p>
                    <p><strong className="text-[var(--text-primary)]">Faction:</strong> Controlled checkpoints</p>
                    <p><strong className="text-[var(--text-primary)]">Contact:</strong> Need introduction</p>
                    <p><strong className="text-[var(--text-primary)]">Hazard:</strong> Environmental danger</p>
                  </div>
                </div>

                <div className="p-3 border border-[var(--border-primary)] rounded bg-[var(--bg-primary)]">
                  <p className="text-xs text-[var(--accent-amber)]">
                    Every blocked route has alternatives or risky traversal options. 
                    The question isn&apos;t &ldquo;can I go?&rdquo; but &ldquo;what does it cost?&rdquo;
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </main>

      {/* Region detail dialog */}
      <Dialog open={!!selectedRegion} onOpenChange={() => setSelectedRegion(null)}>
        <DialogContent className="bg-[var(--bg-secondary)] border-[var(--border-primary)] max-w-lg">
          {selectedRegion && (
            <>
              <DialogHeader>
                <DialogTitle className="text-lg font-bold text-[var(--accent-steel)] tracking-wider terminal-text">
                  {regions[selectedRegion].name.toUpperCase()}
                </DialogTitle>
                <DialogDescription className="text-xs text-[var(--text-muted)]">
                  {regions[selectedRegion].terrain.join(' / ').toUpperCase()}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 mt-4">
                {/* Faction info */}
                <div className="flex items-center gap-3 p-3 border border-[var(--border-primary)] rounded bg-[var(--bg-primary)]">
                  <div 
                    className="w-4 h-4 rounded-full"
                    style={{ 
                      backgroundColor: 
                        {nexus: '#a855f7', ember_colonies: '#f97316', lattice: '#3b82f6', 
                         convergence: '#06b6d4', covenant: '#eab308', wanderers: '#22c55e',
                         cultivators: '#10b981', steel_syndicate: '#ef4444', witnesses: '#f59e0b',
                         architects: '#6366f1', ghost_networks: '#6b7280'}[regions[selectedRegion].primaryFaction] || '#6b7280'
                    }}
                  />
                  <div>
                    <p className="text-sm font-medium">
                      Controlled by {regions[selectedRegion].primaryFaction?.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </p>
                    {regions[selectedRegion].contestedBy && regions[selectedRegion].contestedBy.length > 0 && (
                      <p className="text-xs text-[var(--accent-amber)]">
                        Contested by {regions[selectedRegion].contestedBy?.map(f => f.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')).join(', ')}
                      </p>
                    )}
                  </div>
                </div>

                {/* Description */}
                <div>
                  <h4 className="text-xs font-bold text-[var(--text-muted)] mb-2">DESCRIPTION</h4>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                    {regions[selectedRegion].description}
                  </p>
                </div>

                {/* Character */}
                <div>
                  <h4 className="text-xs font-bold text-[var(--text-muted)] mb-2">ATMOSPHERE</h4>
                  <p className="text-sm text-[var(--text-secondary)] italic border-l-2 border-[var(--border-primary)] pl-3">
                    &ldquo;{regions[selectedRegion].character}&rdquo;
                  </p>
                </div>

                {/* Routes */}
                <div>
                  <h4 className="text-xs font-bold text-[var(--text-muted)] mb-2">CONNECTED REGIONS</h4>
                  <div className="space-y-1.5">
                    {regions[selectedRegion].routes.map((route, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-center justify-between p-2 border border-[var(--border-secondary)] rounded text-sm"
                      >
                        <span className="text-[var(--text-secondary)]">
                          → {route.to.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                        </span>
                        <span className={`text-xs ${
                          route.requirements.length === 0 ? 'text-[var(--accent-green)]' :
                          route.contested ? 'text-[var(--accent-amber)]' :
                          'text-[var(--accent-red)]'
                        }`}>
                          {route.requirements.length === 0 ? 'OPEN' :
                           route.contested ? 'CONTESTED' : 'RESTRICTED'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Points of interest */}
                {regions[selectedRegion].pointsOfInterest.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-[var(--text-muted)] mb-2">POINTS OF INTEREST</h4>
                    <div className="flex flex-wrap gap-2">
                      {regions[selectedRegion].pointsOfInterest.map((poi, idx) => (
                        <span 
                          key={idx}
                          className="text-xs px-2 py-1 rounded bg-[var(--bg-tertiary)] text-[var(--accent-steel)]"
                        >
                          {poi}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex gap-2 pt-2">
                  <Button 
                    className="flex-1 bg-[var(--accent-steel)] hover:bg-[var(--accent-steel)]/80 text-black"
                    onClick={() => setSelectedRegion(null)}
                  >
                    Travel Here
                  </Button>
                  <Button 
                    variant="outline"
                    className="border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]"
                    onClick={() => setSelectedRegion(null)}
                  >
                    Close
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default App;
