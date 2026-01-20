# Sentinel Bridge

Local orchestration layer for SENTINEL. Spawns the Sentinel headless process and exposes a localhost HTTP API for UI integration.

## Philosophy

Per the [cross-platform implementation plan](../architecture/sentinel_cross_platform_implementation_plan.md):

- **Sentinel is the engine** — this layer only translates, never decides
- **Local-first always** — no servers, no accounts, no network required
- **Bridges translate, they do not decide** — no business logic here

## Quick Start

```bash
# From the sentinel-bridge directory
deno task dev
```

This starts the bridge on `http://localhost:3333` and auto-launches Sentinel in headless mode.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/command` | Send command to Sentinel |
| `GET` | `/state` | Get bridge + Sentinel state |
| `GET` | `/events` | SSE stream of game events |
| `POST` | `/start` | Start Sentinel process |
| `POST` | `/stop` | Stop Sentinel process |
| `GET` | `/health` | Health check |

### POST /command

Send a command to Sentinel. Commands mirror the headless.py contract:

```bash
# Get status
curl -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "status"}'

# Say something to the GM
curl -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "say", "text": "I approach the Nexus contact"}'

# Run a slash command
curl -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/jobs", "args": []}'

# Load a campaign
curl -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "load", "campaign_id": "my-campaign"}'

# Save current campaign
curl -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "save"}'
```

### GET /state

Returns current bridge and Sentinel state:

```json
{
  "state": "ready",
  "sentinel": {
    "ok": true,
    "backend": "lmstudio",
    "campaign": {
      "id": "my-campaign",
      "name": "My Campaign",
      "session": 3
    },
    "conversation_length": 12
  },
  "error": null,
  "restartCount": 0,
  "uptime": 45000
}
```

### GET /events

Server-Sent Events stream of game events. Connect with EventSource:

```javascript
const events = new EventSource("http://localhost:3333/events");

events.onmessage = (e) => {
  const event = JSON.parse(e.data);
  console.log("Event:", event.event_type, event.data);
};
```

Events include:
- Game events from Sentinel (faction changes, social energy, etc.)
- Bridge state changes (`bridge_state_change`)

## Configuration

### CLI Options

```bash
deno task start --port 8080 --local --backend lmstudio
```

| Option | Description | Default |
|--------|-------------|---------|
| `--port, -p` | API port | 3333 |
| `--sentinel` | Path to sentinel executable | `sentinel` |
| `--cwd` | Working directory for Sentinel | `../sentinel-agent` |
| `--backend` | LLM backend | `auto` |
| `--local` | Use local mode for smaller models | false |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SENTINEL_PORT` | API port |
| `SENTINEL_PATH` | Path to sentinel executable |
| `SENTINEL_CWD` | Working directory for Sentinel |
| `SENTINEL_BACKEND` | LLM backend |
| `SENTINEL_LOCAL` | Use local mode (`true`/`false`) |

## Error Handling

The bridge handles failures gracefully:

1. **Sentinel crash** — Auto-restarts up to 3 times with exponential backoff
2. **Sentinel unavailable** — API returns 503 with state info
3. **Backend unavailable** — Sentinel continues (state management works)

Check `/state` for current status and any error messages.

## Development

```bash
# Run with file watching (requires denon or similar)
deno task dev

# Run tests
deno task test
```

## Architecture

```
┌─────────────────┐
│   Web UI        │  (Phase 4 - Astro)
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Bridge API     │  ← You are here
│  (Deno)         │
└────────┬────────┘
         │ stdin/stdout (JSON)
         ▼
┌─────────────────┐
│  Sentinel       │  (Python, headless mode)
│  (Engine)       │
└─────────────────┘
```

The bridge is intentionally thin:
- ~300 lines of TypeScript
- No game logic
- No state mutation
- Only process management and HTTP translation

## License

CC BY-NC 4.0 (same as SENTINEL)
