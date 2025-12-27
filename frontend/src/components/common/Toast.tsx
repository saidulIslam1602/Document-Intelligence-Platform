import { useEffect } from 'react';
import { Notification } from '../../hooks/useNotification';

interface ToastProps {
  notification: Notification;
  onClose: (id: string) => void;
}

export default function Toast({ notification, onClose }: ToastProps) {
  useEffect(() => {
    if (notification.duration && notification.duration > 0) {
      const timer = setTimeout(() => {
        onClose(notification.id);
      }, notification.duration);
      
      return () => clearTimeout(timer);
    }
  }, [notification, onClose]);

  const variants = {
    success: 'bg-green-50 border-green-500 text-green-800',
    error: 'bg-red-50 border-red-500 text-red-800',
    warning: 'bg-yellow-50 border-yellow-500 text-yellow-800',
    info: 'bg-blue-50 border-blue-500 text-blue-800',
  };

  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };

  return (
    <div className={`flex items-center gap-3 p-4 rounded-lg border-l-4 shadow-lg ${variants[notification.type]} animate-slide-in`}>
      <span className="text-2xl">{icons[notification.type]}</span>
      <p className="flex-1">{notification.message}</p>
      <button 
        onClick={() => onClose(notification.id)}
        className="text-xl hover:opacity-70"
      >
        ×
      </button>
    </div>
  );
}

