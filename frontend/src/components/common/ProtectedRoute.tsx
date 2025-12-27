import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { canAccessRoute } from '../../utils/roleUtils';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoute?: string;
}

export default function ProtectedRoute({ children, requiredRoute }: ProtectedRouteProps) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRoute && user) {
    const hasAccess = canAccessRoute(user.role, requiredRoute);
    
    if (!hasAccess) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">403</h1>
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Access Denied</h2>
            <p className="text-gray-600 mb-6">
              You don't have permission to access this page.
            </p>
            <p className="text-sm text-gray-500">
              Required role: Admin or Developer
            </p>
            <button
              onClick={() => window.history.back()}
              className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Go Back
            </button>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}

