import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { canAccessRoute } from '../../utils/roleUtils';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  adminOnly?: boolean;
  developerOnly?: boolean;
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/entities', label: 'Entities', icon: '🏷️' },
  { path: '/chat', label: 'AI Chat', icon: '💬' },
  { path: '/search', label: 'Search', icon: '🔍' },
  { path: '/processing-pipeline', label: 'Pipeline', icon: '🔄', developerOnly: true },
  { path: '/workflows', label: 'Workflows', icon: '⚙️', developerOnly: true },
  { path: '/analytics', label: 'Analytics', icon: '📈', developerOnly: true },
  { path: '/mcp-tools', label: 'MCP Tools', icon: '🛠️', developerOnly: true },
  { path: '/webhooks', label: 'Webhooks', icon: '🔗', developerOnly: true },
  { path: '/api-keys', label: 'API Keys', icon: '🔑', developerOnly: true },
  { path: '/audit-logs', label: 'Audit Logs', icon: '📋', developerOnly: true },
  { path: '/admin', label: 'Admin', icon: '👤', adminOnly: true },
  { path: '/settings', label: 'Settings', icon: '⚙' },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const logout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  // Filter navigation items based on user role
  const visibleNavItems = navItems.filter((item) => {
    if (!user) return false;
    
    // Check if user has permission to access this route
    return canAccessRoute(user.role, item.path);
  });

  // Get user role badge color
  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-100 text-red-800';
      case 'developer':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <div className="fixed left-0 top-0 bottom-0 w-64 bg-white dark:bg-gray-800 border-r shadow-sm">
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Document Intelligence
          </h1>
          <p className="text-xs text-gray-500 mt-1">AI-Powered Platform</p>
        </div>
        
        <nav className="px-4 py-4 space-y-1 overflow-y-auto" style={{ height: 'calc(100vh - 180px)' }}>
          {visibleNavItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive(item.path) 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>
        
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t bg-white dark:bg-gray-800">
          <div className="flex items-center gap-3 mb-3 px-2">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium truncate">{user?.username || 'User'}</p>
                {user?.role && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getRoleBadgeColor(user.role)}`}>
                    {user.role}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 truncate">{user?.email || 'user@example.com'}</p>
            </div>
          </div>
          <button 
            onClick={logout} 
            className="w-full px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg font-medium transition-all"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64 p-8">
        <Outlet />
      </div>
    </div>
  );
}

