/**
 * Local HTTP API for Sentinel Bridge
 *
 * Exposes a localhost-only REST API for controlling Sentinel.
 * This allows web UIs to communicate with the engine.
 *
 * Endpoints:
 *   POST /command - Send command to Sentinel
 *   GET  /state   - Get bridge + Sentinel state
 *   GET  /events  - SSE stream of game events
 *   POST /start   - Start Sentinel process
 *   POST /stop    - Stop Sentinel process
 *
 * All endpoints return JSON. CORS is enabled for local development.
 */

import type {
  SentinelCommand,
  GameEvent,
  BridgeStatus,
} from "./types.ts";
import { SentinelProcess, type ProcessConfig } from "./process.ts";

export interface ApiConfig {
  /** Port to listen on (default: 3333) */
  port?: number;
  /** Hostname to bind to (default: localhost) */
  hostname?: string;
  /** Sentinel process configuration */
  sentinel?: ProcessConfig;
}

const DEFAULT_CONFIG: Required<Omit<ApiConfig, "sentinel">> & {
  sentinel: ProcessConfig;
} = {
  port: 3333,
  hostname: "localhost",
  sentinel: {},
};

/**
 * HTTP API server for the Sentinel bridge.
 */
export class BridgeApi {
  private config: typeof DEFAULT_CONFIG;
  private process: SentinelProcess;
  private server: Deno.HttpServer | null = null;

  // SSE clients for event streaming
  private eventClients: Set<ReadableStreamDefaultController<Uint8Array>> =
    new Set();

  constructor(config: ApiConfig = {}) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
      sentinel: { ...DEFAULT_CONFIG.sentinel, ...config.sentinel },
    };

    this.process = new SentinelProcess(this.config.sentinel);

    // Forward events to SSE clients
    this.process.onEvent((event) => this.broadcastEvent(event));
    this.process.onStateChange((state, error) => {
      this.broadcastEvent({
        type: "event",
        event_type: "bridge_state_change",
        data: { state, error },
        campaign_id: null,
        session: null,
        timestamp: new Date().toISOString(),
      });
    });
  }

  /** Start the HTTP server */
  async start(): Promise<void> {
    this.server = Deno.serve(
      {
        port: this.config.port,
        hostname: this.config.hostname,
        onListen: ({ hostname, port }) => {
          console.log(`Bridge API listening on http://${hostname}:${port}`);
        },
      },
      (request) => this.handleRequest(request)
    );

    // Auto-start Sentinel
    try {
      await this.process.start();
    } catch (error) {
      console.error("Failed to start Sentinel:", error);
      // API still runs - clients can check /state for error
    }
  }

  /** Stop the HTTP server and Sentinel process */
  async stop(): Promise<void> {
    await this.process.stop();

    if (this.server) {
      await this.server.shutdown();
      this.server = null;
    }

    // Close all SSE connections
    for (const controller of this.eventClients) {
      try {
        controller.close();
      } catch {
        // Already closed
      }
    }
    this.eventClients.clear();
  }

  private async handleRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;

    // CORS headers for local development
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    // Handle preflight
    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    try {
      let response: Response;

      switch (`${method} ${url.pathname}`) {
        case "POST /command":
          response = await this.handleCommand(request);
          break;
        case "GET /state":
          response = await this.handleState();
          break;
        case "GET /events":
          response = this.handleEvents();
          break;
        case "POST /start":
          response = await this.handleStart();
          break;
        case "POST /stop":
          response = await this.handleStop();
          break;
        case "GET /health":
          response = this.handleHealth();
          break;
        default:
          response = this.json({ error: "Not found" }, 404);
      }

      // Add CORS headers to all responses
      for (const [key, value] of Object.entries(corsHeaders)) {
        response.headers.set(key, value);
      }

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Request error:", message);

      const response = this.json({ error: message }, 500);
      for (const [key, value] of Object.entries(corsHeaders)) {
        response.headers.set(key, value);
      }
      return response;
    }
  }

  private async handleCommand(request: Request): Promise<Response> {
    const body = await request.json();
    const command = body as SentinelCommand;

    if (!command.cmd) {
      return this.json({ ok: false, error: "Missing 'cmd' field" }, 400);
    }

    if (this.process.currentState !== "ready") {
      return this.json(
        {
          ok: false,
          error: `Sentinel is ${this.process.currentState}`,
          state: this.process.currentState,
        },
        503
      );
    }

    try {
      const result = await this.process.send(command);
      return this.json(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return this.json({ ok: false, error: message }, 500);
    }
  }

  private async handleState(): Promise<Response> {
    const sentinelStatus = await this.process.getStatus();

    const status: BridgeStatus = {
      state: this.process.currentState,
      sentinel: sentinelStatus,
      error: this.process.error,
      restartCount: this.process.restarts,
      uptime: this.process.uptime,
    };

    return this.json(status);
  }

  private handleEvents(): Response {
    // Server-Sent Events stream
    const encoder = new TextEncoder();

    const stream = new ReadableStream<Uint8Array>({
      start: (controller) => {
        this.eventClients.add(controller);

        // Send initial connection event
        const event = `data: ${JSON.stringify({
          type: "connected",
          state: this.process.currentState,
        })}\n\n`;
        controller.enqueue(encoder.encode(event));
      },
      cancel: (controller) => {
        this.eventClients.delete(controller as ReadableStreamDefaultController<Uint8Array>);
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  private async handleStart(): Promise<Response> {
    if (this.process.currentState === "ready") {
      return this.json({ ok: true, message: "Already running" });
    }

    try {
      await this.process.start();
      return this.json({ ok: true, state: this.process.currentState });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return this.json({ ok: false, error: message }, 500);
    }
  }

  private async handleStop(): Promise<Response> {
    await this.process.stop();
    return this.json({ ok: true, state: this.process.currentState });
  }

  private handleHealth(): Response {
    return this.json({
      ok: true,
      bridge: "running",
      sentinel: this.process.currentState,
    });
  }

  private broadcastEvent(event: GameEvent): void {
    const encoder = new TextEncoder();
    const data = `data: ${JSON.stringify(event)}\n\n`;
    const encoded = encoder.encode(data);

    for (const controller of this.eventClients) {
      try {
        controller.enqueue(encoded);
      } catch {
        // Client disconnected
        this.eventClients.delete(controller);
      }
    }
  }

  private json(data: unknown, status = 200): Response {
    return new Response(JSON.stringify(data), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }
}
