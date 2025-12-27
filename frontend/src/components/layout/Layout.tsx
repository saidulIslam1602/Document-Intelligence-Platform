import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/batch-upload', label: 'Batch Upload', icon: '📦' },
  { path: '/processing-pipeline', label: 'Pipeline', icon: '🔄' },
  { path: '/workflows', label: 'Workflows', icon: '⚙️' },
  { path: '/entities', label: 'Entities', icon: '🏷️' },
  { path: '/analytics', label: 'Analytics', icon: '📈' },
  { path: '/chat', label: 'AI Chat', icon: '💬' },
  { path: '/search', label: 'Search', icon: '🔍' },
  { path: '/mcp-tools', label: 'MCP Tools', icon: '🛠️' },
  { path: '/webhooks', label: 'Webhooks', icon: '🔗' },
  { path: '/api-keys', label: 'API Keys', icon: '🔑' },
  { path: '/audit-logs', label: 'Audit Logs', icon: '📋' },
  { path: '/admin', label: 'Admin', icon: '👤' },
  { path: '/settings', label: 'Settings', icon: '⚙' },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  const logout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

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
          {navItems.map((item) => (
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
              U
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">User</p>
              <p className="text-xs text-gray-500 truncate">user@example.com</p>
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

