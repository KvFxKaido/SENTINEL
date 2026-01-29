/**
 * SafehouseCanvas — Canvas-based safehouse renderer
 * 
 * Renders the safehouse room with physically placed inventory items.
 * The safehouse is the emotional anchor — a quiet place to account
 * for what you still have.
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import type {
  SafehouseState,
  PlacedObject,
  Point,
  RoomLayout,
  HoverState,
  GearItem,
  Vehicle,
  DormantThread,
  Enhancement,
} from './types';
import { DEFAULT_ROOM_LAYOUT, COLORS } from './types';

interface SafehouseCanvasProps {
  state: SafehouseState;
  width?: number;
  height?: number;
  onObjectClick?: (object: PlacedObject) => void;
  onObjectHover?: (object: PlacedObject | null) => void;
}

// ============================================================================
// Layout Helpers
// ============================================================================

function placeItemsInZone(
  items: Array<{ id: string; data: unknown }>,
  zoneId: string,
  type: PlacedObject['type'],
  layout: RoomLayout
): PlacedObject[] {
  const zone = layout.zones.find(z => z.id === zoneId);
  if (!zone) return [];

  const itemWidth = 60;
  const itemHeight = 40;
  const padding = 10;
  const itemsPerRow = Math.floor((zone.bounds.width - padding * 2) / (itemWidth + padding));

  return items.map((item, index) => {
    const row = Math.floor(index / itemsPerRow);
    const col = index % itemsPerRow;
    const x = zone.bounds.x + padding + col * (itemWidth + padding);
    const y = zone.bounds.y + padding + 30 + row * (itemHeight + padding); // +30 for zone label

    return {
      id: item.id,
      type,
      position: { x, y },
      bounds: { x, y, width: itemWidth, height: itemHeight },
      data: item.data as PlacedObject['data'],
      interactive: true,
      label: getItemLabel(item.data, type),
    };
  });
}

function getItemLabel(data: unknown, type: PlacedObject['type']): string {
  if (!data) return '';
  switch (type) {
    case 'gear':
      return (data as GearItem).name;
    case 'vehicle':
      return (data as Vehicle).name;
    case 'thread':
      return (data as DormantThread).origin;
    case 'enhancement':
      return (data as Enhancement).name;
    default:
      return '';
  }
}

function buildPlacedObjects(state: SafehouseState, layout: RoomLayout): PlacedObject[] {
  const objects: PlacedObject[] = [...layout.furniture];

  // Place gear on workbench
  const gearObjects = placeItemsInZone(
    state.gear.map(g => ({ id: g.id, data: g })),
    'workbench',
    'gear',
    layout
  );
  objects.push(...gearObjects);

  // Place vehicles in garage
  const vehicleObjects = placeItemsInZone(
    state.vehicles.map(v => ({ id: v.id, data: v })),
    'garage',
    'vehicle',
    layout
  );
  objects.push(...vehicleObjects);

  // Place threads on board
  const threadObjects = placeItemsInZone(
    state.threads.map(t => ({ id: t.id, data: t })),
    'board',
    'thread',
    layout
  );
  objects.push(...threadObjects);

  // Place enhancements at medical station
  const enhancementObjects = placeItemsInZone(
    state.enhancements.map(e => ({ id: e.id, data: e })),
    'medical',
    'enhancement',
    layout
  );
  objects.push(...enhancementObjects);

  // Place player character in center
  if (state.character) {
    const centerZone = layout.zones.find(z => z.id === 'center');
    if (centerZone) {
      objects.push({
        id: 'player',
        type: 'player',
        position: {
          x: centerZone.bounds.x + centerZone.bounds.width / 2 - 20,
          y: centerZone.bounds.y + centerZone.bounds.height / 2 - 20,
        },
        bounds: {
          x: centerZone.bounds.x + centerZone.bounds.width / 2 - 20,
          y: centerZone.bounds.y + centerZone.bounds.height / 2 - 20,
          width: 40,
          height: 40,
        },
        interactive: true,
        label: state.character.name,
      });
    }
  }

  return objects;
}

// ============================================================================
// Canvas Rendering
// ============================================================================

function drawRoom(ctx: CanvasRenderingContext2D, layout: RoomLayout) {
  // Background
  ctx.fillStyle = COLORS.bg.primary;
  ctx.fillRect(0, 0, layout.width, layout.height);

  // Floor grid (subtle)
  ctx.strokeStyle = COLORS.bg.tertiary;
  ctx.lineWidth = 1;
  const gridSize = 40;
  for (let x = 0; x < layout.width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, layout.height);
    ctx.stroke();
  }
  for (let y = 0; y < layout.height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(layout.width, y);
    ctx.stroke();
  }

  // Draw zones
  layout.zones.forEach(zone => {
    const zoneColor = COLORS.zones[zone.id as keyof typeof COLORS.zones] || 'rgba(255,255,255,0.05)';
    
    // Zone background
    ctx.fillStyle = zoneColor;
    ctx.fillRect(zone.bounds.x, zone.bounds.y, zone.bounds.width, zone.bounds.height);
    
    // Zone border
    ctx.strokeStyle = COLORS.bg.hover;
    ctx.lineWidth = 1;
    ctx.strokeRect(zone.bounds.x, zone.bounds.y, zone.bounds.width, zone.bounds.height);
    
    // Zone label
    ctx.fillStyle = COLORS.text.muted;
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillText(zone.name.toUpperCase(), zone.bounds.x + 8, zone.bounds.y + 16);
  });
}

function drawObject(
  ctx: CanvasRenderingContext2D,
  obj: PlacedObject,
  isHovered: boolean,
  isSelected: boolean
) {
  const { bounds, type, label } = obj;

  // Object background
  let bgColor = COLORS.bg.secondary;
  let borderColor = COLORS.bg.hover;
  let textColor = COLORS.text.secondary;

  switch (type) {
    case 'gear':
      bgColor = isHovered ? 'rgba(88, 166, 255, 0.3)' : 'rgba(88, 166, 255, 0.15)';
      borderColor = COLORS.accent.blue;
      textColor = COLORS.accent.blue;
      break;
    case 'vehicle':
      bgColor = isHovered ? 'rgba(121, 192, 255, 0.3)' : 'rgba(121, 192, 255, 0.15)';
      borderColor = COLORS.accent.steel;
      textColor = COLORS.accent.steel;
      // Show vehicle status
      const vehicle = obj.data as Vehicle | undefined;
      if (vehicle) {
        if (vehicle.status === 'Broken Down' || vehicle.status === 'Out of Fuel') {
          borderColor = COLORS.status.danger;
          textColor = COLORS.status.danger;
        } else if (vehicle.status === 'Needs Repair' || vehicle.status === 'Low Fuel') {
          borderColor = COLORS.status.warning;
          textColor = COLORS.status.warning;
        }
      }
      break;
    case 'thread':
      bgColor = isHovered ? 'rgba(240, 136, 62, 0.3)' : 'rgba(240, 136, 62, 0.15)';
      borderColor = COLORS.status.special;
      textColor = COLORS.status.special;
      break;
    case 'enhancement':
      bgColor = isHovered ? 'rgba(163, 113, 247, 0.3)' : 'rgba(163, 113, 247, 0.15)';
      borderColor = '#a371f7';
      textColor = '#a371f7';
      break;
    case 'player':
      bgColor = isHovered ? 'rgba(86, 212, 221, 0.4)' : 'rgba(86, 212, 221, 0.25)';
      borderColor = COLORS.accent.cyan;
      textColor = COLORS.accent.cyan;
      break;
    case 'furniture':
      bgColor = COLORS.bg.tertiary;
      borderColor = COLORS.bg.hover;
      textColor = COLORS.text.muted;
      break;
  }

  if (isSelected) {
    borderColor = COLORS.text.primary;
  }

  // Draw object
  ctx.fillStyle = bgColor;
  ctx.fillRect(bounds.x, bounds.y, bounds.width, bounds.height);

  ctx.strokeStyle = borderColor;
  ctx.lineWidth = isHovered || isSelected ? 2 : 1;
  ctx.strokeRect(bounds.x, bounds.y, bounds.width, bounds.height);

  // Draw label (truncated)
  if (label) {
    ctx.fillStyle = textColor;
    ctx.font = '10px "JetBrains Mono", monospace';
    const maxWidth = bounds.width - 8;
    let displayLabel = label;
    while (ctx.measureText(displayLabel).width > maxWidth && displayLabel.length > 3) {
      displayLabel = displayLabel.slice(0, -4) + '...';
    }
    ctx.fillText(displayLabel, bounds.x + 4, bounds.y + bounds.height / 2 + 4);
  }

  // Draw type icon
  const icon = getTypeIcon(type);
  if (icon && type !== 'furniture') {
    ctx.fillStyle = textColor;
    ctx.font = '12px sans-serif';
    ctx.fillText(icon, bounds.x + bounds.width - 16, bounds.y + 14);
  }
}

function getTypeIcon(type: PlacedObject['type']): string {
  switch (type) {
    case 'gear': return '⚙';
    case 'vehicle': return '🚗';
    case 'thread': return '📌';
    case 'enhancement': return '⚡';
    case 'player': return '👤';
    default: return '';
  }
}

function drawEmptyState(ctx: CanvasRenderingContext2D, layout: RoomLayout) {
  ctx.fillStyle = COLORS.text.muted;
  ctx.font = '14px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText('NO DATA AVAILABLE', layout.width / 2, layout.height / 2 - 10);
  ctx.font = '12px "JetBrains Mono", monospace';
  ctx.fillText('Connect to engine to view safehouse', layout.width / 2, layout.height / 2 + 10);
  ctx.textAlign = 'left';
}

// ============================================================================
// Component
// ============================================================================

export function SafehouseCanvas({
  state,
  width = DEFAULT_ROOM_LAYOUT.width,
  height = DEFAULT_ROOM_LAYOUT.height,
  onObjectClick,
  onObjectHover,
}: SafehouseCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<HoverState>({ object: null, position: { x: 0, y: 0 } });
  const [selected, setSelected] = useState<PlacedObject | null>(null);
  const [objects, setObjects] = useState<PlacedObject[]>([]);

  const layout: RoomLayout = {
    ...DEFAULT_ROOM_LAYOUT,
    width,
    height,
  };

  // Build placed objects when state changes
  useEffect(() => {
    const placedObjects = buildPlacedObjects(state, layout);
    setObjects(placedObjects);
  }, [state, width, height]);

  // Render canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear and draw
    ctx.clearRect(0, 0, width, height);
    drawRoom(ctx, layout);

    if (!state.character && state.gear.length === 0) {
      drawEmptyState(ctx, layout);
      return;
    }

    // Draw all objects
    objects.forEach(obj => {
      const isHovered = hover.object?.id === obj.id;
      const isSelected = selected?.id === obj.id;
      drawObject(ctx, obj, isHovered, isSelected);
    });
  }, [objects, hover, selected, width, height, state]);

  // Hit testing
  const findObjectAtPoint = useCallback((point: Point): PlacedObject | null => {
    // Check in reverse order (top-most first)
    for (let i = objects.length - 1; i >= 0; i--) {
      const obj = objects[i];
      if (!obj.interactive) continue;
      const { bounds } = obj;
      if (
        point.x >= bounds.x &&
        point.x <= bounds.x + bounds.width &&
        point.y >= bounds.y &&
        point.y <= bounds.y + bounds.height
      ) {
        return obj;
      }
    }
    return null;
  }, [objects]);

  // Mouse handlers
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const point: Point = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    const obj = findObjectAtPoint(point);
    setHover({ object: obj, position: point });
    onObjectHover?.(obj);

    // Update cursor
    canvas.style.cursor = obj?.interactive ? 'pointer' : 'default';
  }, [findObjectAtPoint, onObjectHover]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const point: Point = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    const obj = findObjectAtPoint(point);
    if (obj?.interactive) {
      setSelected(obj);
      onObjectClick?.(obj);
    } else {
      setSelected(null);
    }
  }, [findObjectAtPoint, onObjectClick]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        setHover({ object: null, position: { x: 0, y: 0 } });
        onObjectHover?.(null);
      }}
      onClick={handleClick}
      style={{
        display: 'block',
        background: COLORS.bg.primary,
      }}
    />
  );
}
