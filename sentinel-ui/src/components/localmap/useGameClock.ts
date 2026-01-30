/**
 * Game Clock Hook (Phase 2)
 * 
 * Local game time that:
 * - Advances with player movement/actions
 * - Pauses during dialogue and menus
 * - Triggers time-based events
 * 
 * Time scale: 1 real second = 1 game minute (when not paused)
 */

import { useState, useCallback, useEffect, useRef } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface GameTime {
  day: number;
  hour: number;
  minute: number;
}

export interface GameClockState {
  time: GameTime;
  paused: boolean;
  pauseReason: string | null;
  totalMinutes: number;
}

export interface GameClockActions {
  pause: (reason?: string) => void;
  resume: () => void;
  advanceTime: (minutes: number) => void;
  setTime: (time: GameTime) => void;
}

export type TimeOfDay = 'dawn' | 'morning' | 'midday' | 'afternoon' | 'evening' | 'night';

// ============================================================================
// Constants
// ============================================================================

const MINUTES_PER_HOUR = 60;
const HOURS_PER_DAY = 24;
const MINUTES_PER_DAY = MINUTES_PER_HOUR * HOURS_PER_DAY;

// Real-time to game-time ratio (1 real second = 1 game minute)
const TIME_SCALE = 1;

// ============================================================================
// Utilities
// ============================================================================

export function timeToMinutes(time: GameTime): number {
  return (time.day * MINUTES_PER_DAY) + (time.hour * MINUTES_PER_HOUR) + time.minute;
}

export function minutesToTime(totalMinutes: number): GameTime {
  const day = Math.floor(totalMinutes / MINUTES_PER_DAY);
  const remaining = totalMinutes % MINUTES_PER_DAY;
  const hour = Math.floor(remaining / MINUTES_PER_HOUR);
  const minute = remaining % MINUTES_PER_HOUR;
  return { day, hour, minute };
}

export function formatTime(time: GameTime): string {
  const hourStr = time.hour.toString().padStart(2, '0');
  const minuteStr = time.minute.toString().padStart(2, '0');
  return `Day ${time.day + 1} - ${hourStr}:${minuteStr}`;
}

export function formatTimeShort(time: GameTime): string {
  const hourStr = time.hour.toString().padStart(2, '0');
  const minuteStr = time.minute.toString().padStart(2, '0');
  return `${hourStr}:${minuteStr}`;
}

export function getTimeOfDay(hour: number): TimeOfDay {
  if (hour >= 5 && hour < 7) return 'dawn';
  if (hour >= 7 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 14) return 'midday';
  if (hour >= 14 && hour < 18) return 'afternoon';
  if (hour >= 18 && hour < 21) return 'evening';
  return 'night';
}

export function getAmbientLightForTime(hour: number): number {
  // Returns 0-1 ambient light level based on time
  const timeOfDay = getTimeOfDay(hour);
  switch (timeOfDay) {
    case 'dawn': return 0.4;
    case 'morning': return 0.8;
    case 'midday': return 1.0;
    case 'afternoon': return 0.9;
    case 'evening': return 0.5;
    case 'night': return 0.2;
  }
}

// ============================================================================
// Hook
// ============================================================================

export interface UseGameClockOptions {
  initialTime?: GameTime;
  autoAdvance?: boolean;  // Auto-advance time in real-time
  onTimeChange?: (time: GameTime, totalMinutes: number) => void;
  onHourChange?: (hour: number, timeOfDay: TimeOfDay) => void;
  onDayChange?: (day: number) => void;
}

export function useGameClock(options: UseGameClockOptions = {}): [GameClockState, GameClockActions] {
  const {
    initialTime = { day: 0, hour: 8, minute: 0 },
    autoAdvance = true,
    onTimeChange,
    onHourChange,
    onDayChange,
  } = options;

  const [time, setTime] = useState<GameTime>(initialTime);
  const [paused, setPaused] = useState(false);
  const [pauseReason, setPauseReason] = useState<string | null>(null);
  
  const lastHourRef = useRef(initialTime.hour);
  const lastDayRef = useRef(initialTime.day);
  const intervalRef = useRef<number | null>(null);

  const totalMinutes = timeToMinutes(time);

  // Advance time by minutes
  const advanceTime = useCallback((minutes: number) => {
    setTime(prevTime => {
      const newTotal = timeToMinutes(prevTime) + minutes;
      const newTime = minutesToTime(Math.max(0, newTotal));
      
      // Trigger callbacks
      if (newTime.hour !== lastHourRef.current) {
        lastHourRef.current = newTime.hour;
        onHourChange?.(newTime.hour, getTimeOfDay(newTime.hour));
      }
      
      if (newTime.day !== lastDayRef.current) {
        lastDayRef.current = newTime.day;
        onDayChange?.(newTime.day);
      }
      
      onTimeChange?.(newTime, newTotal);
      
      return newTime;
    });
  }, [onTimeChange, onHourChange, onDayChange]);

  // Pause clock
  const pause = useCallback((reason?: string) => {
    setPaused(true);
    setPauseReason(reason || 'paused');
  }, []);

  // Resume clock
  const resume = useCallback(() => {
    setPaused(false);
    setPauseReason(null);
  }, []);

  // Set time directly
  const setTimeDirectly = useCallback((newTime: GameTime) => {
    setTime(newTime);
    lastHourRef.current = newTime.hour;
    lastDayRef.current = newTime.day;
    onTimeChange?.(newTime, timeToMinutes(newTime));
  }, [onTimeChange]);

  // Auto-advance timer
  useEffect(() => {
    if (!autoAdvance || paused) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Advance 1 game minute per real second
    intervalRef.current = window.setInterval(() => {
      advanceTime(TIME_SCALE);
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoAdvance, paused, advanceTime]);

  const state: GameClockState = {
    time,
    paused,
    pauseReason,
    totalMinutes,
  };

  const actions: GameClockActions = {
    pause,
    resume,
    advanceTime,
    setTime: setTimeDirectly,
  };

  return [state, actions];
}

// ============================================================================
// Time-Based Event System
// ============================================================================

export interface TimeEvent {
  id: string;
  triggerMinutes: number;  // Total minutes when event triggers
  repeating: boolean;
  repeatInterval?: number; // Minutes between repeats
  callback: () => void;
  triggered: boolean;
}

export function useTimeEvents(totalMinutes: number, paused: boolean) {
  const eventsRef = useRef<Map<string, TimeEvent>>(new Map());
  const [triggered, setTriggered] = useState<string[]>([]);

  // Register a time event
  const registerEvent = useCallback((event: Omit<TimeEvent, 'triggered'>) => {
    eventsRef.current.set(event.id, { ...event, triggered: false });
  }, []);

  // Unregister a time event
  const unregisterEvent = useCallback((eventId: string) => {
    eventsRef.current.delete(eventId);
  }, []);

  // Check and trigger events
  useEffect(() => {
    if (paused) return;

    const newTriggered: string[] = [];

    eventsRef.current.forEach((event, id) => {
      if (event.triggered && !event.repeating) return;

      const shouldTrigger = event.repeating
        ? totalMinutes >= event.triggerMinutes && 
          (totalMinutes - event.triggerMinutes) % (event.repeatInterval || 60) === 0
        : totalMinutes >= event.triggerMinutes && !event.triggered;

      if (shouldTrigger) {
        event.callback();
        event.triggered = true;
        newTriggered.push(id);
        
        // Update trigger time for repeating events
        if (event.repeating && event.repeatInterval) {
          event.triggerMinutes = totalMinutes + event.repeatInterval;
          event.triggered = false;
        }
      }
    });

    if (newTriggered.length > 0) {
      setTriggered(prev => [...prev, ...newTriggered]);
    }
  }, [totalMinutes, paused]);

  return { registerEvent, unregisterEvent, triggered };
}
