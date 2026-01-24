/**
 * Sentinel Process Manager
 *
 * Spawns and manages the Sentinel headless process.
 * Handles lifecycle, IPC, and crash recovery.
 *
 * Key principle: This layer ONLY translates - it never interprets game rules
 * or mutates state without Sentinel's consent.
 */

import type {
  SentinelCommand,
  SentinelResponse,
  GameEvent,
  ProcessState,
  StatusResponse,
} from "./types.ts";

/**
 * Find the sentinel executable in common installation locations.
 * Returns the first path that exists, or "sentinel" to fall back to PATH.
 */
async function findSentinelExecutable(): Promise<string> {
  const isWindows = Deno.build.os === "windows";
  const exe = isWindows ? "sentinel.exe" : "sentinel";
  const candidates: string[] = [];

  if (isWindows) {
    // Windows: Check Python Scripts directories
    const appData = Deno.env.get("APPDATA");
    const localAppData = Deno.env.get("LOCALAPPDATA");
    const userProfile = Deno.env.get("USERPROFILE");

    // Common Python version patterns
    const pyVersions = ["Python314", "Python313", "Python312", "Python311", "Python310"];

    for (const ver of pyVersions) {
      if (appData) {
        candidates.push(`${appData}\\Python\\${ver}\\Scripts\\${exe}`);
      }
      if (localAppData) {
        candidates.push(`${localAppData}\\Programs\\Python\\${ver}\\Scripts\\${exe}`);
      }
      // System-wide Python installs
      candidates.push(`C:\\${ver}\\Scripts\\${exe}`);
      candidates.push(`C:\\Program Files\\${ver}\\Scripts\\${exe}`);
    }

    // pipx location
    if (userProfile) {
      candidates.push(`${userProfile}\\.local\\bin\\${exe}`);
    }
  } else {
    // Unix: Check common locations
    const home = Deno.env.get("HOME");
    if (home) {
      candidates.push(`${home}/.local/bin/${exe}`);
      candidates.push(`${home}/.pyenv/shims/${exe}`);
    }
    candidates.push(`/usr/local/bin/${exe}`);
    candidates.push(`/usr/bin/${exe}`);
  }

  // Check each candidate
  for (const path of candidates) {
    try {
      const stat = await Deno.stat(path);
      if (stat.isFile) {
        console.log(`Auto-detected sentinel at: ${path}`);
        return path;
      }
    } catch {
      // File doesn't exist, try next
    }
  }

  // Fall back to PATH lookup
  return "sentinel";
}

export interface ProcessConfig {
  /** Path to sentinel executable or 'sentinel' if in PATH */
  sentinelPath?: string;
  /** Working directory for Sentinel (defaults to sentinel-agent) */
  cwd?: string;
  /** Use local mode for smaller models */
  localMode?: boolean;
  /** Specific backend to use */
  backend?: string;
  /** Max restart attempts before giving up */
  maxRestarts?: number;
  /** Delay between restart attempts (ms) */
  restartDelay?: number;
}

const DEFAULT_CONFIG: Required<ProcessConfig> = {
  sentinelPath: "sentinel",
  cwd: "../sentinel-agent",
  localMode: false,
  backend: "auto",
  maxRestarts: 3,
  restartDelay: 1000,
};

type EventCallback = (event: GameEvent) => void;
type StateCallback = (state: ProcessState, error?: string) => void;

/**
 * Manages the Sentinel headless process.
 *
 * Usage:
 *   const process = new SentinelProcess();
 *   process.onEvent((event) => console.log(event));
 *   await process.start();
 *   const result = await process.send({ cmd: "status" });
 */
export class SentinelProcess {
  private process: Deno.ChildProcess | null = null;
  private stdin: WritableStreamDefaultWriter<Uint8Array> | null = null;
  private config: Required<ProcessConfig>;

  private state: ProcessState = "stopped";
  private startTime: number | null = null;
  private restartCount = 0;
  private lastError: string | null = null;

  private eventCallbacks: EventCallback[] = [];
  private stateCallbacks: StateCallback[] = [];
  private pendingRequests: Map<
    number,
    { resolve: (r: SentinelResponse) => void; reject: (e: Error) => void }
  > = new Map();
  private requestId = 0;
  private responseBuffer = "";

  // Ready signal handling
  private readyResolver: (() => void) | null = null;
  private readyRejector: ((e: Error) => void) | null = null;

  constructor(config: ProcessConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /** Current process state */
  get currentState(): ProcessState {
    return this.state;
  }

  /** Uptime in milliseconds, or null if not running */
  get uptime(): number | null {
    return this.startTime ? Date.now() - this.startTime : null;
  }

  /** Number of restarts since initial start */
  get restarts(): number {
    return this.restartCount;
  }

  /** Last error message, if any */
  get error(): string | null {
    return this.lastError;
  }

  /** Register callback for game events */
  onEvent(callback: EventCallback): void {
    this.eventCallbacks.push(callback);
  }

  /** Register callback for state changes */
  onStateChange(callback: StateCallback): void {
    this.stateCallbacks.push(callback);
  }

  /** Start the Sentinel process */
  async start(): Promise<void> {
    if (this.state === "ready" || this.state === "starting") {
      return;
    }

    this.setState("starting");
    this.lastError = null;

    // Auto-detect sentinel path if using default
    if (this.config.sentinelPath === "sentinel") {
      this.config.sentinelPath = await findSentinelExecutable();
    }

    try {
      await this.spawn();
      await this.waitForReady();
      this.startTime = Date.now();
      this.setState("ready");
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.lastError = msg;
      this.setState("error", msg);
      throw error;
    }
  }

  /** Stop the Sentinel process gracefully */
  async stop(): Promise<void> {
    if (!this.process) {
      this.setState("stopped");
      return;
    }

    try {
      // Try graceful shutdown first
      await this.send({ cmd: "quit" });
      // Give it a moment to exit
      await new Promise((r) => setTimeout(r, 500));
    } catch {
      // Ignore send errors during shutdown
    }

    // Force kill if still running
    try {
      this.process.kill("SIGTERM");
    } catch {
      // Process may already be dead
    }

    this.cleanup();
    this.setState("stopped");
  }

  /** Send a command and wait for response */
  async send(command: SentinelCommand): Promise<SentinelResponse> {
    if (this.state !== "ready") {
      throw new Error(`Cannot send command: process is ${this.state}`);
    }

    if (!this.stdin) {
      throw new Error("No stdin available");
    }

    const id = ++this.requestId;

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });

      const line = JSON.stringify(command) + "\n";
      const encoder = new TextEncoder();

      this.stdin!.write(encoder.encode(line)).catch((err) => {
        this.pendingRequests.delete(id);
        reject(err);
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error("Request timed out"));
        }
      }, 30000);
    });
  }

  /** Get current status from Sentinel */
  async getStatus(): Promise<StatusResponse | null> {
    if (this.state !== "ready") {
      return null;
    }

    try {
      const response = await this.send({ cmd: "status" });
      if (response.ok) {
        return response as unknown as StatusResponse;
      }
    } catch {
      // Status check failed
    }

    return null;
  }

  private setState(state: ProcessState, error?: string): void {
    this.state = state;
    for (const callback of this.stateCallbacks) {
      try {
        callback(state, error);
      } catch {
        // Don't let callback errors break the state machine
      }
    }
  }

  private async spawn(): Promise<void> {
    const args = ["--headless"];
    if (this.config.localMode) {
      args.push("--local");
    }
    if (this.config.backend !== "auto") {
      args.push("--backend", this.config.backend);
    }

    const command = new Deno.Command(this.config.sentinelPath, {
      args,
      cwd: this.config.cwd,
      stdin: "piped",
      stdout: "piped",
      stderr: "piped",
    });

    this.process = command.spawn();
    this.stdin = this.process.stdin.getWriter();

    // Start reading stdout
    this.readStdout();
    // Log stderr (but don't block on it)
    this.readStderr();

    // Handle process exit
    this.process.status.then((status) => {
      if (this.state === "ready") {
        // Unexpected exit - attempt restart
        console.error(`Sentinel exited unexpectedly with code ${status.code}`);
        this.handleCrash();
      }
    });
  }

  private async readStdout(): Promise<void> {
    if (!this.process) return;

    const decoder = new TextDecoder();
    const reader = this.process.stdout.getReader();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        this.responseBuffer += decoder.decode(value, { stream: true });
        this.processBuffer();
      }
    } catch (error) {
      if (this.state === "ready") {
        console.error("Error reading stdout:", error);
      }
    }
  }

  private async readStderr(): Promise<void> {
    if (!this.process) return;

    const decoder = new TextDecoder();
    const reader = this.process.stderr.getReader();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        if (text.trim()) {
          console.error("[Sentinel stderr]", text);
        }
      }
    } catch {
      // Ignore stderr read errors
    }
  }

  private processBuffer(): void {
    // Handle both Unix (\n) and Windows (\r\n) line endings
    const lines = this.responseBuffer.split(/\r?\n/);
    this.responseBuffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      try {
        const response = JSON.parse(trimmed) as SentinelResponse;
        this.handleResponse(response);
      } catch (error) {
        console.error("Failed to parse response:", trimmed, error);
      }
    }
  }

  private handleResponse(response: SentinelResponse): void {
    if (response.type === "ready") {
      // Ready signal - resolve the waiting promise
      if (this.readyResolver) {
        this.readyResolver();
        this.readyResolver = null;
        this.readyRejector = null;
      }
    } else if (response.type === "event") {
      // Game event - notify callbacks
      const event = response as unknown as GameEvent;
      for (const callback of this.eventCallbacks) {
        try {
          callback(event);
        } catch {
          // Don't let callback errors break event processing
        }
      }
    } else if (response.type === "result" || response.type === "error") {
      // Command response - resolve oldest pending request
      // (Sentinel processes commands in order)
      const entries = this.pendingRequests.entries();
      const first = entries.next();
      if (!first.done) {
        const [id, { resolve }] = first.value;
        this.pendingRequests.delete(id);
        resolve(response);
      }
    }
  }

  private waitForReady(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.readyResolver = null;
        this.readyRejector = null;
        reject(new Error("Timeout waiting for Sentinel to be ready"));
      }, 10000);

      // Store resolvers so handleResponse can call them
      this.readyResolver = () => {
        clearTimeout(timeout);
        resolve();
      };
      this.readyRejector = (error: Error) => {
        clearTimeout(timeout);
        reject(error);
      };
    });
  }

  private async handleCrash(): Promise<void> {
    this.cleanup();

    if (this.restartCount >= this.config.maxRestarts) {
      const msg = `Max restarts (${this.config.maxRestarts}) exceeded`;
      this.lastError = msg;
      this.setState("error", msg);
      return;
    }

    this.restartCount++;
    console.log(
      `Restarting Sentinel (attempt ${this.restartCount}/${this.config.maxRestarts})...`
    );

    await new Promise((r) => setTimeout(r, this.config.restartDelay));

    try {
      await this.start();
    } catch (error) {
      console.error("Restart failed:", error);
    }
  }

  private cleanup(): void {
    this.stdin = null;
    this.process = null;
    this.responseBuffer = "";

    // Reject all pending requests
    for (const [, { reject }] of this.pendingRequests) {
      reject(new Error("Process terminated"));
    }
    this.pendingRequests.clear();
  }
}
