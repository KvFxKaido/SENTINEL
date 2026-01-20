# Sentinel UI

Web interface for SENTINEL — connects to the Deno bridge to control the game.

## Architecture

```
┌─────────────────┐
│  Astro UI       │  ← You are here
│  (localhost:4321)
└────────┬────────┘
         │ HTTP (proxied to /api)
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

## Development

```bash
npm run dev      # Start dev server with hot reload
npm run build    # Build for production
npm run preview  # Preview production build
```

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| `GameLayout.astro` | Layout | Dark tactical theme, CSS variables |
| `Header.astro` | Static | Title, connection status |
| `NarrativeLog.astro` | Static | Conversation history |
| `SidePanel.astro` | Static | State, factions, events |
| `CommandInput.astro` | Interactive | Text input, quick commands |

## API Client

`src/lib/bridge.ts` provides typed functions for the bridge API:

```typescript
import { say, slash, status, getState, subscribeToEvents } from './lib/bridge';

// Send message to GM
const result = await say("I approach the Nexus contact");

// Run slash command
const jobs = await slash("jobs");

// Subscribe to live events
const cleanup = subscribeToEvents((event) => {
  console.log(event.event_type, event.data);
});
```

## Theme

CSS variables in `GameLayout.astro`:

| Variable | Color | Use |
|----------|-------|-----|
| `--bg-primary` | #0d1117 | Main background |
| `--bg-secondary` | #161b22 | Panel backgrounds |
| `--accent-steel` | #79c0ff | Primary accent |
| `--accent-cyan` | #56d4dd | Secondary accent |
| `--status-danger` | #f85149 | Errors, warnings |

## License

CC BY-NC 4.0 (same as SENTINEL)
