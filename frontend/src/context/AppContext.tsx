import { createContext, useContext, ReactNode } from 'react';
import { useNotification } from '../hooks/useNotification';
import { useAuth } from '../hooks/useAuth';
import ToastContainer from '../components/common/ToastContainer';

interface AppContextType {
  notification: ReturnType<typeof useNotification>;
  auth: ReturnType<typeof useAuth>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const notification = useNotification();
  const auth = useAuth();

  return (
    <AppContext.Provider value={{ notification, auth }}>
      {children}
      <ToastContainer 
        notifications={notification.notifications}
        onClose={notification.remove}
      />
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}

