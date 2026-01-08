/**
 * useNotification Hook
 *
 * Generic notification system with queue management.
 * Supports multiple notification types with configurable icons, colors, and durations.
 *
 * Usage:
 *   const { showNotification } = useNotification();
 *   showNotification({
 *     message: 'Consist 10 selected',
 *     type: 'info',
 *     duration: 2500
 *   });
 */

import { createContext, useContext, useState } from 'react';

const NotificationContext = createContext();

// Preset configurations for notification types
const NOTIFICATION_TYPES = {
  success: {
    icon: 'fa-circle-check',
    iconClass: 'text-signal-green',
    borderClass: 'border-signal-green/30',
  },
  info: {
    icon: 'fa-circle-check',
    iconClass: 'text-signal-amber',
    borderClass: 'border-signal-amber/30',
  },
  warning: {
    icon: 'fa-exclamation-triangle',
    iconClass: 'text-amber-500',
    borderClass: 'border-amber-500/30',
  },
  error: {
    icon: 'fa-circle-xmark',
    iconClass: 'text-signal-red',
    borderClass: 'border-signal-red/30',
  },
};

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);

  const showNotification = ({ message, type = 'info', icon, duration = 2000 }) => {
    // Generate unique ID for this notification
    const id = Date.now() + Math.random();

    // Get preset config or use defaults
    const config = NOTIFICATION_TYPES[type] || NOTIFICATION_TYPES.info;
    const finalIcon = icon || config.icon;

    const notification = {
      id,
      message,
      type,
      icon: finalIcon,
      iconClass: config.iconClass,
      borderClass: config.borderClass,
      duration,
    };

    // Add to queue
    setNotifications(prev => [...prev, notification]);

    // Auto-dismiss after duration
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, duration);
  };

  return (
    <NotificationContext.Provider value={{ notifications, showNotification }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
}
