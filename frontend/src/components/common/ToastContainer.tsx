import Toast from './Toast';
import { Notification } from '../../hooks/useNotification';

interface ToastContainerProps {
  notifications: Notification[];
  onClose: (id: string) => void;
}

export default function ToastContainer({ notifications, onClose }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {notifications.map(notification => (
        <Toast key={notification.id} notification={notification} onClose={onClose} />
      ))}
    </div>
  );
}

