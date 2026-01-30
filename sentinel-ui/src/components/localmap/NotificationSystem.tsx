import { useEffect, useRef } from 'react';
import type { ConsequenceNotification } from './consequences';
import { getFactionColor } from './consequences';
import './notifications.css';

interface NotificationSystemProps {
  notifications: ConsequenceNotification[];
  onDismiss: (id: string) => void;
  onHighlight: (notification: ConsequenceNotification) => void;
}

const TYPE_LABELS: Record<string, string> = {
  faction_shift: 'Faction Shift',
  npc_moved: 'NPC Moved',
  thread_surfaced: 'Thread Surfaced',
  hinge_locked: 'Hinge Locked',
  combat_consequence: 'Combat Consequence',
};

export function NotificationSystem({
  notifications,
  onDismiss,
  onHighlight,
}: NotificationSystemProps) {
  const timersRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    const activeIds = new Set(notifications.map(notification => notification.id));
    for (const [id, timerId] of timersRef.current.entries()) {
      if (!activeIds.has(id)) {
        window.clearTimeout(timerId);
        timersRef.current.delete(id);
      }
    }

    for (const notification of notifications) {
      if (timersRef.current.has(notification.id)) continue;
      const timerId = window.setTimeout(() => {
        timersRef.current.delete(notification.id);
        onDismiss(notification.id);
      }, 5000);
      timersRef.current.set(notification.id, timerId);
    }
  }, [notifications, onDismiss]);

  useEffect(() => {
    return () => {
      for (const timerId of timersRef.current.values()) {
        window.clearTimeout(timerId);
      }
      timersRef.current.clear();
    };
  }, []);

  return (
    <div className="notification-stack">
      {notifications.slice(0, 3).map(notification => {
        const severityClass = notification.severity
          ? `notification-severity-${notification.severity}`
          : 'notification-severity-info';
        const title = notification.title || TYPE_LABELS[notification.type] || 'Update';
        const accent = notification.factionId
          ? getFactionColor(notification.factionId)
          : '#58a6ff';

        return (
          <div
            key={notification.id}
            className={`notification-card ${severityClass}`}
            style={{ '--accent': accent } as React.CSSProperties}
            onClick={() => onHighlight(notification)}
            role="button"
            tabIndex={0}
            onKeyDown={event => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onHighlight(notification);
              }
            }}
          >
            <p className="notification-title">{title}</p>
            <p className="notification-message">{notification.message}</p>
            <div className="notification-meta">
              {notification.mapId ? notification.mapId.replace(/_/g, ' ') : 'off-screen'}
            </div>
          </div>
        );
      })}
    </div>
  );
}
