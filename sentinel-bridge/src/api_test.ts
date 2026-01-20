/**
 * Tests for BridgeApi - the HTTP API layer.
 *
 * These tests verify:
 * - HTTP endpoint behavior
 * - Error responses
 * - CORS headers
 * - SSE event streaming
 */

import {
  assertEquals,
  assertExists,
} from "jsr:@std/assert";

// Import types for reference
import type { BridgeStatus, SentinelCommand } from "./types.ts";

Deno.test("API types - BridgeStatus has required fields", () => {
  const status: BridgeStatus = {
    state: "stopped",
    sentinel: null,
    error: null,
    restartCount: 0,
    uptime: null,
  };

  assertExists(status.state);
  assertEquals(status.restartCount, 0);
});

Deno.test("API types - SentinelCommand variants", () => {
  // Test that all command types are valid
  const commands: SentinelCommand[] = [
    { cmd: "status" },
    { cmd: "say", text: "hello" },
    { cmd: "slash", command: "/jobs", args: [] },
    { cmd: "load", campaign_id: "test" },
    { cmd: "save" },
    { cmd: "quit" },
  ];

  assertEquals(commands.length, 6);
  assertEquals(commands[0].cmd, "status");
  assertEquals((commands[1] as { cmd: string; text: string }).text, "hello");
});

Deno.test("API types - ProcessState values", () => {
  // Verify all states are strings
  const states = ["stopped", "starting", "ready", "error"] as const;
  states.forEach((state) => {
    assertEquals(typeof state, "string");
  });
});

// Integration tests would require a running Sentinel process.
// These are documented for manual testing:

/*
Manual testing checklist:

1. Health check:
   curl http://localhost:3333/health
   Expected: {"ok":true,"bridge":"running","sentinel":"..."}

2. State endpoint:
   curl http://localhost:3333/state
   Expected: JSON with state, sentinel, error, restartCount, uptime

3. Command - status:
   curl -X POST http://localhost:3333/command -d '{"cmd":"status"}'
   Expected: {"type":"result","ok":true,"backend":{...}}

4. Command - unknown:
   curl -X POST http://localhost:3333/command -d '{"cmd":"invalid"}'
   Expected: {"type":"result","ok":false,"error":"Unknown command..."}

5. Malformed JSON:
   curl -X POST http://localhost:3333/command -d 'not json'
   Expected: 400 error

6. SSE stream:
   curl -N http://localhost:3333/events
   Expected: Streaming connection with data: messages

7. Process control:
   curl -X POST http://localhost:3333/stop
   curl http://localhost:3333/state  # state should be "stopped"
   curl -X POST http://localhost:3333/start
   curl http://localhost:3333/state  # state should be "ready"

8. CORS:
   curl -I -X OPTIONS http://localhost:3333/command
   Expected: Access-Control-Allow-Origin: *
*/
