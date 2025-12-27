import { useState } from 'react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { useAuth } from '../hooks/useAuth';
import { hasPermission } from '../utils/roleUtils';

export default function Settings() {
  const [darkMode, setDarkMode] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [autoProcess, setAutoProcess] = useState(true);
  const { user } = useAuth();
  
  const canViewSensitive = user ? hasPermission(user.role, 'viewSensitiveData') : false;
  const canConfigureWebhooks = user ? hasPermission(user.role, 'configureWebhooks') : false;

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-3xl font-bold">Settings</h1>

      <Card title="Account Settings">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input 
              type="email" 
              defaultValue="user@example.com"
              className="w-full px-3 py-2 border rounded-lg" 
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input 
              type="text" 
              defaultValue="user"
              className="w-full px-3 py-2 border rounded-lg" 
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input 
              type="password" 
              placeholder="••••••••"
              className="w-full px-3 py-2 border rounded-lg" 
            />
          </div>
          
          <Button>Save Changes</Button>
        </div>
      </Card>

      <Card title="Preferences">
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <p className="font-medium">Dark Mode</p>
              <p className="text-sm text-gray-500">Switch to dark theme</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={darkMode}
                onChange={(e) => setDarkMode(e.target.checked)}
                className="sr-only peer" 
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex justify-between items-center">
            <div>
              <p className="font-medium">Email Notifications</p>
              <p className="text-sm text-gray-500">Receive email updates</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={notifications}
                onChange={(e) => setNotifications(e.target.checked)}
                className="sr-only peer" 
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex justify-between items-center">
            <div>
              <p className="font-medium">Auto-Process Documents</p>
              <p className="text-sm text-gray-500">Automatically process uploaded documents</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoProcess}
                onChange={(e) => setAutoProcess(e.target.checked)}
                className="sr-only peer" 
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </Card>

      {canConfigureWebhooks && (
        <Card title="API Configuration">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">API Endpoint</label>
              <input 
                type="text" 
                defaultValue="http://localhost:8003"
                className="w-full px-3 py-2 border rounded-lg font-mono text-sm" 
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Webhook URL</label>
              <input 
                type="text" 
                placeholder="https://your-domain.com/webhook"
                className="w-full px-3 py-2 border rounded-lg font-mono text-sm" 
              />
            </div>
            
            <Button variant="secondary">Test Connection</Button>
          </div>
        </Card>
      )}

      <Card title="Data & Privacy">
        <div className="space-y-3">
          <Button variant="secondary" className="w-full">
            Export My Data
          </Button>
          <Button variant="secondary" className="w-full">
            Download My Activity Log
          </Button>
          {canViewSensitive && (
            <Button variant="danger" className="w-full">
              Delete Account
            </Button>
          )}
        </div>
      </Card>

      {canViewSensitive && (
        <Card title="System Information">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Version</span>
              <span className="font-medium">2.0.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">API Version</span>
              <span className="font-medium">v1</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Environment</span>
              <span className="font-medium">Development</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">User Role</span>
              <span className="font-medium capitalize">{user?.role}</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

