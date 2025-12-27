import { useState, useCallback } from 'react';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  duration?: number;
}

export function useNotification() {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const show = useCallback((type: NotificationType, message: string, duration = 5000) => {
    const id = Math.random().toString(36).substr(2, 9);
    const notification: Notification = { id, type, message, duration };
    
    setNotifications(prev => [...prev, notification]);

    if (duration > 0) {
      setTimeout(() => {
        remove(id);
      }, duration);
    }

    return id;
  }, []);

  const remove = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const success = useCallback((message: string, duration?: number) => {
    return show('success', message, duration);
  }, [show]);

  const error = useCallback((message: string, duration?: number) => {
    return show('error', message, duration);
  }, [show]);

  const warning = useCallback((message: string, duration?: number) => {
    return show('warning', message, duration);
  }, [show]);

  const info = useCallback((message: string, duration?: number) => {
    return show('info', message, duration);
  }, [show]);

  return {
    notifications,
    show,
    remove,
    success,
    error,
    warning,
    info
  };
}

