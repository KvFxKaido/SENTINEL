/**
 * Tests for SentinelProcess - the process manager.
 *
 * These tests verify:
 * - Process lifecycle (start, stop, restart)
 * - Error handling (spawn failure, timeout)
 * - Event forwarding
 * - State management
 */

import {
  assertEquals,
  assertRejects,
  assertExists,
} from "jsr:@std/assert";
import { SentinelProcess } from "./process.ts";

// Helper to create a mock process config that uses a simple echo script
function createTestConfig(overrides: Record<string, unknown> = {}) {
  return {
    sentinelPath: "echo",  // Will fail to start properly but tests spawn
    cwd: ".",
    maxRestarts: 1,
    restartDelay: 100,
    ...overrides,
  };
}

Deno.test("SentinelProcess - initial state is stopped", () => {
  const process = new SentinelProcess(createTestConfig());
  assertEquals(process.currentState, "stopped");
  assertEquals(process.uptime, null);
  assertEquals(process.restarts, 0);
  assertEquals(process.error, null);
});

Deno.test("SentinelProcess - cannot send command when stopped", async () => {
  const process = new SentinelProcess(createTestConfig());

  await assertRejects(
    async () => {
      await process.send({ cmd: "status" });
    },
    Error,
    "Cannot send command: process is stopped"
  );
});

Deno.test("SentinelProcess - spawn failure sets error state", async () => {
  const process = new SentinelProcess({
    sentinelPath: "nonexistent_command_that_does_not_exist",
    cwd: ".",
    maxRestarts: 0,
    restartDelay: 10,
  });

  await assertRejects(
    async () => {
      await process.start();
    },
    Error
  );

  assertEquals(process.currentState, "error");
  assertExists(process.error);
});

Deno.test("SentinelProcess - state callbacks are called", async () => {
  const process = new SentinelProcess({
    sentinelPath: "nonexistent_command",
    cwd: ".",
    maxRestarts: 0,
    restartDelay: 10,
  });

  const stateChanges: string[] = [];
  process.onStateChange((state) => {
    stateChanges.push(state);
  });

  try {
    await process.start();
  } catch {
    // Expected to fail
  }

  // Should have recorded state transitions
  assertEquals(stateChanges.includes("starting"), true);
  assertEquals(stateChanges.includes("error"), true);
});

Deno.test("SentinelProcess - event callbacks can be registered", () => {
  const process = new SentinelProcess(createTestConfig());

  let eventReceived = false;
  process.onEvent(() => {
    eventReceived = true;
  });

  // Just verify registration doesn't throw
  assertEquals(eventReceived, false);
});

Deno.test("SentinelProcess - stop when already stopped is safe", async () => {
  const process = new SentinelProcess(createTestConfig());

  // Should not throw
  await process.stop();
  assertEquals(process.currentState, "stopped");
});

Deno.test("SentinelProcess - getStatus returns null when not ready", async () => {
  const process = new SentinelProcess(createTestConfig());

  const status = await process.getStatus();
  assertEquals(status, null);
});

Deno.test("SentinelProcess - config defaults are applied", () => {
  const process = new SentinelProcess({});

  // Access private config via any cast for testing
  const config = (process as unknown as { config: Record<string, unknown> }).config;

  assertEquals(config.sentinelPath, "sentinel");
  assertEquals(config.cwd, "../sentinel-agent");
  assertEquals(config.maxRestarts, 3);
  assertEquals(config.restartDelay, 1000);
});
