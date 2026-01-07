import { useState, useEffect, useCallback, useRef } from 'react';
import type { GameState, Message, NPC, Disposition, MissionPhase } from '../types';

const WS_URL = 'ws://localhost:8765';
const RECONNECT_DELAY = 3000;

interface ServerMessage {
  type: 'state' | 'narrative' | 'choice' | 'npc' | 'response' | 'pong';
  data?: ServerGameState;
  content?: string;
  options?: string[];
  npc?: {
    name: string;
    faction: string;
    disposition: string;
    role?: string;
  };
}

interface ServerGameState {
  campaign: {
    name: string;
    session: number;
    phase: string;
  };
  character: {
    name: string;
    background: string;
    socialEnergy: number;
  };
  factions: Record<string, string>;
  session: {
    missionId: string;
    missionTitle: string;
    phase: string;
  };
  loadout: Array<{
    id: string;
    name: string;
    singleUse: boolean;
    used: boolean;
  }>;
  activeNpc: {
    name: string;
    faction: string;
    disposition: string;
    role?: string;
  } | null;
}

function transformServerState(server: ServerGameState): GameState {
  return {
    campaign: {
      name: server.campaign?.name || 'No Campaign',
      session: server.campaign?.session || 0,
      phase: (server.campaign?.phase || 'briefing') as MissionPhase,
    },
    character: {
      name: server.character?.name || 'Unknown',
      background: server.character?.background || 'Unknown',
      socialEnergy: server.character?.socialEnergy || 100,
    },
    factions: Object.fromEntries(
      Object.entries(server.factions || {}).map(([k, v]) => [k, v as Disposition])
    ),
    loadout: server.loadout?.map(item => item.name) || [],
    activeNpc: server.activeNpc ? {
      name: server.activeNpc.name,
      faction: server.activeNpc.faction,
      disposition: server.activeNpc.disposition as Disposition,
      portrait: null,
      role: server.activeNpc.role,
    } : null,
  };
}

export function useGameSocket() {
  const [connected, setConnected] = useState(false);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [codecNpc, setCodecNpc] = useState<{ npc: NPC; dialogue: string } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to SENTINEL server');
      setConnected(true);
      // Request initial state
      ws.send(JSON.stringify({ type: 'get_state' }));
    };

    ws.onclose = () => {
      console.log('Disconnected from SENTINEL server');
      setConnected(false);
      wsRef.current = null;

      // Auto-reconnect
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('Attempting to reconnect...');
        connect();
      }, RECONNECT_DELAY);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data);
        handleMessage(msg);
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };
  }, []);

  const handleMessage = useCallback((msg: ServerMessage) => {
    switch (msg.type) {
      case 'state':
        if (msg.data) {
          setGameState(transformServerState(msg.data));
        }
        break;

      case 'narrative':
        if (msg.content) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            type: 'narrative',
            content: msg.content!,
            timestamp: new Date(),
          }]);
        }
        break;

      case 'choice':
        if (msg.content) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            type: 'choice',
            content: msg.content!,
            options: msg.options || [],
            timestamp: new Date(),
          }]);
        }
        break;

      case 'npc':
        if (msg.npc && msg.content) {
          setCodecNpc({
            npc: {
              name: msg.npc.name,
              faction: msg.npc.faction,
              disposition: msg.npc.disposition as Disposition,
              portrait: null,
              role: msg.npc.role,
            },
            dialogue: msg.content,
          });
        }
        break;

      case 'response':
        if (msg.content) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            type: 'system',
            content: msg.content!,
            timestamp: new Date(),
          }]);
        }
        break;

      case 'pong':
        // Connection alive
        break;
    }
  }, []);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'command',
        command,
      }));

      // Add player message to local state
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'player',
        content: command,
        timestamp: new Date(),
      }]);
    }
  }, []);

  const sendInput = useCallback((input: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'input',
        input,
      }));

      // Add player message to local state
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'player',
        content: input,
        timestamp: new Date(),
      }]);
    }
  }, []);

  const closeCodec = useCallback(() => {
    setCodecNpc(null);
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    connected,
    gameState,
    messages,
    codecNpc,
    sendCommand,
    sendInput,
    closeCodec,
  };
}
