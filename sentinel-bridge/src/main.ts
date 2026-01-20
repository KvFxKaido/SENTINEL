/**
 * Sentinel Bridge - Main Entry Point
 *
 * Starts the local HTTP API server that manages the Sentinel process.
 *
 * Usage:
 *   deno task dev           # Development mode
 *   deno task start         # Production mode
 *
 * Environment variables:
 *   SENTINEL_PORT      - API port (default: 3333)
 *   SENTINEL_PATH      - Path to sentinel executable
 *   SENTINEL_CWD       - Working directory for Sentinel
 *   SENTINEL_BACKEND   - Backend to use (auto, lmstudio, ollama, etc.)
 *   SENTINEL_LOCAL     - Use local mode for 8B-12B models (true/false)
 */

import { BridgeApi } from "./api.ts";
import { parseArgs } from "jsr:@std/cli/parse-args";

function printUsage(): void {
  console.log(`
Sentinel Bridge - Local orchestration layer for SENTINEL

Usage:
  deno task start [options]

Options:
  --port, -p <number>     Port to listen on (default: 3333)
  --sentinel <path>       Path to sentinel executable
  --cwd <path>            Working directory for Sentinel
  --backend <name>        Backend to use (auto, lmstudio, ollama, etc.)
  --local                 Use local mode for smaller models
  --help, -h              Show this help message

Environment variables:
  SENTINEL_PORT           Same as --port
  SENTINEL_PATH           Same as --sentinel
  SENTINEL_CWD            Same as --cwd
  SENTINEL_BACKEND        Same as --backend
  SENTINEL_LOCAL          Same as --local (set to 'true')

Examples:
  deno task start
  deno task start --port 8080 --local
  deno task start --sentinel /path/to/sentinel --backend lmstudio
`);
}

async function main(): Promise<void> {
  const args = parseArgs(Deno.args, {
    string: ["port", "sentinel", "cwd", "backend"],
    boolean: ["local", "help"],
    alias: {
      p: "port",
      h: "help",
    },
  });

  if (args.help) {
    printUsage();
    Deno.exit(0);
  }

  // Build config from args and environment
  const port =
    Number(args.port) ||
    Number(Deno.env.get("SENTINEL_PORT")) ||
    3333;

  const sentinelPath =
    args.sentinel ||
    Deno.env.get("SENTINEL_PATH") ||
    "sentinel";

  const cwd =
    args.cwd ||
    Deno.env.get("SENTINEL_CWD") ||
    "../sentinel-agent";

  const backend =
    args.backend ||
    Deno.env.get("SENTINEL_BACKEND") ||
    "auto";

  const localMode =
    args.local ||
    Deno.env.get("SENTINEL_LOCAL") === "true";

  console.log("Starting Sentinel Bridge...");
  console.log(`  Port: ${port}`);
  console.log(`  Sentinel: ${sentinelPath}`);
  console.log(`  CWD: ${cwd}`);
  console.log(`  Backend: ${backend}`);
  console.log(`  Local mode: ${localMode}`);
  console.log("");

  const api = new BridgeApi({
    port,
    hostname: "localhost",
    sentinel: {
      sentinelPath,
      cwd,
      backend,
      localMode,
    },
  });

  // Handle graceful shutdown
  const shutdown = async () => {
    console.log("\nShutting down...");
    await api.stop();
    Deno.exit(0);
  };

  // Windows only supports SIGINT (ctrl-c) and SIGBREAK (ctrl-break)
  Deno.addSignalListener("SIGINT", shutdown);
  if (Deno.build.os !== "windows") {
    Deno.addSignalListener("SIGTERM", shutdown);
  }

  await api.start();

  console.log("");
  console.log("Endpoints:");
  console.log(`  POST http://localhost:${port}/command  - Send command to Sentinel`);
  console.log(`  GET  http://localhost:${port}/state    - Get bridge state`);
  console.log(`  GET  http://localhost:${port}/events   - SSE event stream`);
  console.log(`  POST http://localhost:${port}/start    - Start Sentinel`);
  console.log(`  POST http://localhost:${port}/stop     - Stop Sentinel`);
  console.log(`  GET  http://localhost:${port}/health   - Health check`);
  console.log("");
  console.log("Press Ctrl+C to stop");
}

// Run
main().catch((error) => {
  console.error("Fatal error:", error);
  Deno.exit(1);
});
