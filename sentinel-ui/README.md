# Sentinel UI

Web interface for SENTINEL — a TUI-style browser UI that connects to the Deno bridge.

## Screenshots

Note: This ASCII mock-up is illustrative. The UI is still partially reactive and
uses placeholder metadata in some panels.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SENTINEL │ ● ready │     Cipher (Session 5)     │ Backend: claude (sonnet) │
├──────────┬──────────────────────────────────────────────────────┬───────────┤
│   SELF   │                    NARRATIVE                         │   WORLD   │
├──────────┤                                                      ├───────────┤
│ CIPHER   │  > YOU                                               │ STANDINGS │
│ [Ghost]  │  │ /start                                            │           │
│          │                                                      │ Steel Sy. │
│ STATUS   │  ◆ GM                                                │ Witnesses │
│ Pistach. │  │ The derelict transit hub smells like wet          │ Ember Co. │
│ Credits  │  │ concrete and ozone...                             │ Wanderers │
│ Location │                                                      │ ...       │
│ Region   │  **What do you do?**                                 │           │
│          │  1. Slip out through the north exit                  │ THREADS   │
│ LOADOUT  │  2. Hold position and let them pass                  │ [None]    │
│ > Laptop │  3. Sabotage the hauler's engine                     │           │
│   Drone  │  4. Something else...                                │ EVENTS    │
│   Kit    │                                                      │ loaded    │
├──────────┴──────────────────────────────────────────────────────┴───────────┤
│ > Enter command or message...                              [SEND]           │
│ QUICK: /status  /jobs  /wiki  /save  /help                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────────┐
│  Astro UI       │  ← You are here
│  (localhost:4321)
└────────┬────────┘
         │ HTTP (fetch to localhost:3333)
         ▼
┌─────────────────┐
│  Deno Bridge    │
│  (localhost:3333)
└────────┬────────┘
         │ stdin/stdout (JSON)
         ▼
┌─────────────────┐
│  Sentinel       │
│  (Python)       │
└─────────────────┘
```

## Quick Start

```bash
# 1. Start the Deno bridge (in another terminal)
cd ../sentinel-bridge
deno task dev

# 2. Install dependencies
npm install

# 3. Start the dev server
npm run dev
```

Open http://localhost:4321

## Layout

The UI uses a 3-column TUI-style layout:

| Column | Content | Updates |
|--------|---------|---------|
| **SELF** (left) | Character name, background, status (pistachios, credits), location, loadout, enhancements | Refreshes after specific commands or select bridge events |
| **NARRATIVE** (center) | Conversation log with GM responses | Appends on command/message (local, no backfill) |
| **WORLD** (right) | Faction standings with progress bars, active threads, event stream | Refreshes after specific commands or select bridge events |

### Message Types

| Role | Style | Notes |
|------|-------|-------|
| Player | Codec frame | Defaults to `YOU` + placeholder faction/portrait; header text is decorative |
| GM | Codec frame | Name is parsed when response starts with `Name:` and mapped to campaign NPC metadata; `npc.interrupt` events render as incoming transmissions |
| System | Centered, muted | Command outputs or system notices |
| Error | Red | Failed commands or bridge errors |

## Components

| Component | Purpose |
|-----------|---------|
| `GameLayout.astro` | AMOLED dark theme, CSS variables, 3-column grid |
| `Header.astro` | Status bar: SENTINEL │ status │ campaign │ backend |
| `CodecFrame.astro` | MGS-style codec frame used for dialogue cards |
| `NarrativeLog.astro` | Narrative container + welcome splash (messages inserted client-side) |
| `CommandInput.astro` | Prompt input + command dispatch + codec card rendering |
| `index.astro` | Main page with SELF/WORLD panels, state management |

## API Client

`src/lib/bridge.ts` provides typed functions:

```typescript
import { say, slash, status, getState, getCampaignState, subscribeToEvents } from './lib/bridge';

// Send message to GM
const result = await say("I approach the Nexus contact");
// Returns: { ok: true, response: "The contact looks up..." }

// Run slash command
const jobs = await slash("jobs");

// Get detailed campaign state
const state = await getCampaignState();
// Returns: character, factions, gear, enhancements, etc.

// Subscribe to live events (SSE)
const cleanup = subscribeToEvents((event) => {
  console.log(event.event_type, event.data);
});
```

## State Refresh

The UI refreshes state automatically after certain commands:

| Command | Refreshes |
|---------|-----------|
| `/load`, `/new` | Bridge state + Campaign state |
| `/start`, `/save`, `/jobs`, `/shop`, `/roll` | Campaign state |
| `/backend` | Bridge state |
| Any message to GM | Campaign state |

The UI also refreshes campaign state on select SSE events:

`campaign.loaded`, `faction.changed`, `social_energy.changed`, `session.started`, `session.ended`.

## Theme

AMOLED-optimized dark theme with CSS variables:

| Variable | Color | Use |
|----------|-------|-----|
| `--bg-primary` | `#000000` | True black background |
| `--bg-secondary` | `#0a0a0a` | Panel backgrounds |
| `--bg-tertiary` | `#121212` | Hover states |
| `--accent-steel` | `#79c0ff` | Primary accent (GM, borders) |
| `--accent-cyan` | `#56d4dd` | Secondary accent (titles, prompt) |
| `--status-danger` | `#f85149` | Errors, hostile factions |

### Faction Standing Colors

| Standing | Color | CSS Class |
|----------|-------|-----------|
| Allied | Green | `.standing-allied` |
| Friendly | Cyan | `.standing-friendly` |
| Neutral | Gray | `.standing-neutral` |
| Unfriendly | Orange | `.standing-unfriendly` |
| Hostile | Red | `.standing-hostile` |

## Development

```bash
npm run dev      # Start dev server with hot reload
npm run build    # Build for production
npm run preview  # Preview production build
```

## License

CC BY-NC 4.0 (same as SENTINEL)
