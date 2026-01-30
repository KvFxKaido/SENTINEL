import { useEffect, useMemo, useRef } from 'react';
import type { LocalMapTemplate } from './types';
import type { FactionPressure, FactionPressureZone } from './consequences';
import { buildPressureZones, getFactionColor } from './consequences';

interface FactionPressureOverlayProps {
  map: LocalMapTemplate;
  pressures: FactionPressure[];
  zones?: FactionPressureZone[];
  tileSize: number;
  active?: boolean;
}

export function FactionPressureOverlay({
  map,
  pressures,
  zones,
  tileSize,
  active = true,
}: FactionPressureOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const renderZones = useMemo(() => {
    if (zones && zones.length > 0) return zones;
    return buildPressureZones(map, pressures);
  }, [map, pressures, zones]);

  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = map.width * tileSize;
    const height = map.height * tileSize;

    let rafId = 0;
    const needsAnimation = renderZones.some(zone => zone.direction === 'rising');

    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);

      for (const zone of renderZones) {
        const baseColor = getFactionColor(zone.factionId);
        const baseAlpha = 0.03 + (zone.level / 100) * 0.12;
        const pulse = zone.direction === 'rising'
          ? 0.75 + 0.25 * Math.sin(time / 550)
          : 1;

        const alpha = baseAlpha * pulse * (zone.direction === 'falling' ? 0.6 : 1);

        ctx.fillStyle = applyAlpha(baseColor, alpha);
        const x = zone.bounds.col * tileSize;
        const y = zone.bounds.row * tileSize;
        ctx.fillRect(x, y, zone.bounds.width * tileSize, zone.bounds.height * tileSize);

        if (zone.direction === 'falling') {
          ctx.fillStyle = 'rgba(120, 120, 120, 0.04)';
          ctx.fillRect(x, y, zone.bounds.width * tileSize, zone.bounds.height * tileSize);
        }
      }
    };

    const loop = (time: number) => {
      draw(time);
      rafId = requestAnimationFrame(loop);
    };

    if (needsAnimation) {
      rafId = requestAnimationFrame(loop);
    } else {
      draw(performance.now());
    }

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [active, map, renderZones, tileSize]);

  return (
    <canvas
      ref={canvasRef}
      width={map.width * tileSize}
      height={map.height * tileSize}
      className="localmap-layer localmap-layer-pressure"
    />
  );
}

function applyAlpha(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const safeAlpha = Math.max(0, Math.min(1, alpha));
  return `rgba(${r}, ${g}, ${b}, ${safeAlpha})`;
}
