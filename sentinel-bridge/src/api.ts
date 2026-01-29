/**
 * Local HTTP API for Sentinel Bridge
 *
 * Exposes a localhost-only REST API for controlling Sentinel.
 * This allows web UIs to communicate with the engine.
 *
 * Endpoints:
 *   POST /command       - Send command to Sentinel
 *   GET  /state         - Get bridge + Sentinel state
 *   GET  /events        - SSE stream of game events
 *   GET  /map           - Get complete map state
 *   GET  /map/region/:id - Get detailed region info
 *   POST /start         - Start Sentinel process
 *   POST /stop          - Stop Sentinel process
 *
 * All endpoints return JSON. CORS is enabled for local development.
 */

import type {
  SentinelCommand,
  GameEvent,
  BridgeStatus,
} from "./types.ts";
import { SentinelProcess, type ProcessConfig } from "./process.ts";
import { Wiki, type WikiPage, type WikiSearchResult } from "./wiki.ts";
import { join, dirname, fromFileUrl } from "https://deno.land/std@0.208.0/path/mod.ts";

export interface ApiConfig {
  /** Port to listen on (default: 3333) */
  port?: number;
  /** Hostname to bind to (default: localhost) */
  hostname?: string;
  /** Sentinel process configuration */
  sentinel?: ProcessConfig;
  /** Path to wiki root directory (default: auto-detected) */
  wikiPath?: string;
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
  private wiki: Wiki;
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

    // Initialize wiki with auto-detected path if not provided
    const wikiPath = config.wikiPath || this.detectWikiPath();
    this.wiki = new Wiki({ wikiPath });
    console.log(`Wiki path: ${wikiPath}`);

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

      // Check for dynamic path routes first
      if (method === "GET" && url.pathname === "/map") {
        response = await this.handleMapState();
      } else if (method === "GET" && url.pathname.startsWith("/map/region/")) {
        response = await this.handleMapRegion(url);
      } else if (method === "GET" && url.pathname.startsWith("/wiki/page/")) {
        response = await this.handleWikiPage(url);
      } else if (method === "GET" && url.pathname === "/wiki/search") {
        response = await this.handleWikiSearch(url);
      } else if (method === "GET" && url.pathname.startsWith("/wiki/list/")) {
        response = await this.handleWikiList(url);
      } else {
        // Static routes
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

  /**
   * Auto-detect wiki path by looking for wiki/ directory relative to bridge
   */
  private detectWikiPath(): string {
    // Try to find wiki relative to this file's location
    // Bridge is at: SENTINEL/sentinel-bridge/src/api.ts
    // Wiki is at: SENTINEL/wiki/
    try {
      const moduleDir = dirname(fromFileUrl(import.meta.url));
      const bridgeRoot = dirname(moduleDir);
      const projectRoot = dirname(bridgeRoot);
      return join(projectRoot, "wiki");
    } catch {
      // Fallback to relative path
      return join(Deno.cwd(), "..", "wiki");
    }
  }

  // ─── Map Endpoints (Sentinel 2D) ──────────────────────────────────────────────

  /**
   * GET /map
   * Returns complete map state with all regions, connectivity, and content markers.
   */
  private async handleMapState(): Promise<Response> {
    if (this.process.currentState !== "ready") {
      return this.json(
        { ok: false, error: `Sentinel is ${this.process.currentState}` },
        503
      );
    }

    try {
      const result = await this.process.send({ cmd: "map_state" });
      return this.json(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return this.json({ ok: false, error: message }, 500);
    }
  }

  /**
   * GET /map/region/:id
   * Returns detailed info for a specific region including route feasibility.
   */
  private async handleMapRegion(url: URL): Promise<Response> {
    const pathMatch = url.pathname.match(/^\/map\/region\/(.+)$/);
    if (!pathMatch) {
      return this.json({ error: "Invalid map region path" }, 400);
    }

    const regionId = decodeURIComponent(pathMatch[1]);

    if (this.process.currentState !== "ready") {
      return this.json(
        { ok: false, error: `Sentinel is ${this.process.currentState}` },
        503
      );
    }

    try {
      const result = await this.process.send({
        cmd: "map_region",
        region_id: regionId,
      });
      return this.json(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return this.json({ ok: false, error: message }, 500);
    }
  }

  // ─── Wiki Endpoints ─────────────────────────────────────────────────────────

  /**
   * GET /wiki/page/:name?campaign=cipher
   * Retrieve a single wiki page
   */
  private async handleWikiPage(url: URL): Promise<Response> {
    // Extract page name from path: /wiki/page/Wei -> Wei
    const pathMatch = url.pathname.match(/^\/wiki\/page\/(.+)$/);
    if (!pathMatch) {
      return this.json({ error: "Invalid wiki page path" }, 400);
    }

    const pageName = decodeURIComponent(pathMatch[1]);
    const campaignId = url.searchParams.get("campaign") || undefined;

    const page = await this.wiki.getPage(pageName, campaignId);

    if (!page) {
      return this.json({ error: `Page not found: ${pageName}` }, 404);
    }

    return this.json({
      ok: true,
      page: {
        name: page.name,
        path: page.path,
        source: page.source,
        type: page.type,
        frontmatter: page.frontmatter,
        content: page.content,
      },
    });
  }

  /**
   * GET /wiki/search?q=query&campaign=cipher&limit=10
   * Search wiki pages
   */
  private async handleWikiSearch(url: URL): Promise<Response> {
    const query = url.searchParams.get("q") || "";
    const campaignId = url.searchParams.get("campaign") || undefined;
    const limit = parseInt(url.searchParams.get("limit") || "10");

    if (!query || query.length < 2) {
      return this.json({ error: "Query must be at least 2 characters" }, 400);
    }

    const results = await this.wiki.search(query, campaignId, limit);

    return this.json({
      ok: true,
      query,
      count: results.length,
      results,
    });
  }

  /**
   * GET /wiki/list/:category?campaign=cipher
   * List pages in a category (npcs, factions, characters)
   */
  private async handleWikiList(url: URL): Promise<Response> {
    // Extract category from path: /wiki/list/npcs -> npcs
    const pathMatch = url.pathname.match(/^\/wiki\/list\/(.+)$/);
    if (!pathMatch) {
      return this.json({ error: "Invalid wiki list path" }, 400);
    }

    const category = pathMatch[1].toLowerCase();
    const campaignId = url.searchParams.get("campaign") || undefined;

    const validCategories = ["npcs", "factions", "characters", "threads", "hinges"];
    if (!validCategories.includes(category)) {
      return this.json({
        error: `Invalid category: ${category}. Valid: ${validCategories.join(", ")}`,
      }, 400);
    }

    const pages = await this.wiki.listPages(category, campaignId);

    return this.json({
      ok: true,
      category,
      count: pages.length,
      pages: pages.map((p) => ({
        name: p.name,
        path: p.path,
        source: p.source,
        type: p.type,
        frontmatter: p.frontmatter,
      })),
    });
  }
}
