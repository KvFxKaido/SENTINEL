/**
 * Types for the Safehouse Canvas View
 * 
 * The safehouse is the emotional anchor of the spatial layer.
 * Inventory is physically placed in the room — gear on tables,
 * vehicles visible, favors pinned on boards.
 */

// ============================================================================
// Inventory Items
// ============================================================================

export interface GearItem {
  id: string;
  name: string;
  category: string;
  description?: string;
  used: boolean;
  singleUse?: boolean;
}

export interface Vehicle {
  id: string;
  name: string;
  type: string;
  description?: string;
  fuel: number;
  condition: number;
  status: 'Operational' | 'Low Fuel' | 'Needs Repair' | 'Out of Fuel' | 'Broken Down';
  terrain: string[];
  capacity: number;
  cargo: boolean;
  stealth: boolean;
}

export interface Enhancement {
  id: string;
  name: string;
  source: string;
  benefit: string;
}

export interface DormantThread {
  id: string;
  origin: string;
  trigger: string;
  consequence: string;
  severity: string;
  createdSession: number;
}

// ============================================================================
// Safehouse State
// ============================================================================

export interface SafehouseState {
  character: {
    name: string;
    background: string;
    credits: number;
    socialEnergy: {
      current: number;
      max: number;
    };
  } | null;
  gear: GearItem[];
  vehicles: Vehicle[];
  enhancements: Enhancement[];
  threads: DormantThread[];
  region: string;
  location: string;
}

// ============================================================================
// Canvas Rendering
// ============================================================================

export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** A physical object placed in the safehouse */
export interface PlacedObject {
  id: string;
  type: 'gear' | 'vehicle' | 'thread' | 'enhancement' | 'player' | 'furniture';
  position: Point;
  bounds: Rect;
  data?: GearItem | Vehicle | DormantThread | Enhancement;
  sprite?: string;
  label?: string;
  interactive: boolean;
}

/** Room zones where items are placed */
export interface RoomZone {
  id: string;
  name: string;
  bounds: Rect;
  accepts: PlacedObject['type'][];
}

/** The safehouse room layout */
export interface RoomLayout {
  width: number;
  height: number;
  zones: RoomZone[];
  furniture: PlacedObject[];
}

// ============================================================================
// Interaction
// ============================================================================

export interface HoverState {
  object: PlacedObject | null;
  position: Point;
}

export interface SelectionState {
  object: PlacedObject | null;
}

// ============================================================================
// Room Layout Constants
// ============================================================================

/** Default safehouse room layout */
export const DEFAULT_ROOM_LAYOUT: RoomLayout = {
  width: 800,
  height: 600,
  zones: [
    // Workbench area for gear
    {
      id: 'workbench',
      name: 'Workbench',
      bounds: { x: 50, y: 100, width: 300, height: 150 },
      accepts: ['gear'],
    },
    // Garage area for vehicles
    {
      id: 'garage',
      name: 'Garage',
      bounds: { x: 450, y: 100, width: 300, height: 200 },
      accepts: ['vehicle'],
    },
    // Board for threads and obligations
    {
      id: 'board',
      name: 'Planning Board',
      bounds: { x: 50, y: 300, width: 200, height: 200 },
      accepts: ['thread'],
    },
    // Medical station for enhancements
    {
      id: 'medical',
      name: 'Medical Station',
      bounds: { x: 300, y: 350, width: 150, height: 150 },
      accepts: ['enhancement'],
    },
    // Center area for player
    {
      id: 'center',
      name: 'Center',
      bounds: { x: 300, y: 200, width: 200, height: 150 },
      accepts: ['player'],
    },
  ],
  furniture: [
    // Static furniture pieces
    {
      id: 'table',
      type: 'furniture',
      position: { x: 100, y: 120 },
      bounds: { x: 100, y: 120, width: 200, height: 80 },
      interactive: false,
      label: 'Workbench',
    },
    {
      id: 'corkboard',
      type: 'furniture',
      position: { x: 60, y: 310 },
      bounds: { x: 60, y: 310, width: 180, height: 150 },
      interactive: false,
      label: 'Planning Board',
    },
  ],
};

// ============================================================================
// Color Palette (matches CSS variables)
// ============================================================================

export const COLORS = {
  bg: {
    primary: '#000000',
    secondary: '#0a0a0a',
    tertiary: '#121212',
    hover: '#1a1a1a',
  },
  text: {
    primary: '#e6edf3',
    secondary: '#8b949e',
    muted: '#6e7681',
  },
  accent: {
    blue: '#58a6ff',
    steel: '#79c0ff',
    cyan: '#56d4dd',
  },
  status: {
    success: '#3fb950',
    warning: '#d29922',
    danger: '#f85149',
    info: '#58a6ff',
    special: '#f0883e',
  },
  zones: {
    workbench: 'rgba(88, 166, 255, 0.1)',
    garage: 'rgba(121, 192, 255, 0.1)',
    board: 'rgba(240, 136, 62, 0.1)',
    medical: 'rgba(163, 113, 247, 0.1)',
    center: 'rgba(86, 212, 221, 0.1)',
  },
};
