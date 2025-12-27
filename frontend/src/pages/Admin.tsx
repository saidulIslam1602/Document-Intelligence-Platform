import { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import api from '../services/api';

export default function Admin() {
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    loadSystemHealth();
    loadUsers();
    loadLogs();
  }, []);

  const loadSystemHealth = async () => {
    try {
      const res = await api.get('/admin/health');
      setSystemHealth(res.data);
    } catch (error) {
      console.error('Failed to load system health');
      // Mock data for demo
      setSystemHealth({
        apiGateway: 'online',
        documentProcessor: 'online',
        aiEngine: 'online',
        database: 'online',
        redis: 'online'
      });
    }
  };

  const loadUsers = async () => {
    try {
      const res = await api.get('/admin/users');
      setUsers(res.data.users || []);
    } catch (error) {
      setUsers([
        { id: '1', email: 'admin@example.com', role: 'admin', status: 'active' },
        { id: '2', email: 'user@example.com', role: 'user', status: 'active' },
      ]);
    }
  };

  const loadLogs = async () => {
    try {
      const res = await api.get('/admin/logs?limit=10');
      setLogs(res.data.logs || []);
    } catch (error) {
      setLogs([
        { id: '1', timestamp: new Date(), level: 'info', message: 'Document processed successfully', service: 'document-processor' },
        { id: '2', timestamp: new Date(), level: 'warning', message: 'High memory usage detected', service: 'ai-engine' },
        { id: '3', timestamp: new Date(), level: 'error', message: 'Failed to connect to external API', service: 'api-gateway' },
      ]);
    }
  };

  const getHealthBadge = (status: string) => {
    return status === 'online' ? 'success' : 'error';
  };

  const getLevelBadge = (level: string) => {
    switch(level) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      default: return 'info';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">System Administration</h1>
        <Button variant="danger">Emergency Stop</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <p className="text-sm text-gray-500">Total Users</p>
          <p className="text-3xl font-bold">{users.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Uptime</p>
          <p className="text-3xl font-bold">99.9%</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">API Calls Today</p>
          <p className="text-3xl font-bold">15,247</p>
        </Card>
      </div>

      <Card title="System Health">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {systemHealth && Object.entries(systemHealth).map(([service, status]) => (
            <div key={service} className="text-center p-4 bg-gray-50 rounded-lg">
              <Badge variant={getHealthBadge(status as string)}>
                {status as string}
              </Badge>
              <p className="text-sm font-medium mt-2 capitalize">
                {service.replace(/([A-Z])/g, ' $1').trim()}
              </p>
            </div>
          ))}
        </div>
      </Card>

      <Card title="User Management">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left py-3">Email</th>
              <th className="text-left py-3">Role</th>
              <th className="text-left py-3">Status</th>
              <th className="text-left py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id} className="border-b">
                <td className="py-3">{user.email}</td>
                <td className="py-3">
                  <Badge variant="info">{user.role}</Badge>
                </td>
                <td className="py-3">
                  <Badge variant={user.status === 'active' ? 'success' : 'error'}>
                    {user.status}
                  </Badge>
                </td>
                <td className="py-3">
                  <Button variant="secondary" className="text-xs">
                    Edit
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Recent Logs">
        <div className="space-y-2">
          {logs.map(log => (
            <div key={log.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
              <Badge variant={getLevelBadge(log.level)}>
                {log.level}
              </Badge>
              <div className="flex-1">
                <p className="text-sm font-medium">{log.message}</p>
                <p className="text-xs text-gray-500">
                  {log.service} • {new Date(log.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
        <Button variant="secondary" className="w-full mt-4">
          View All Logs
        </Button>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Database Stats">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Total Documents</span>
              <span className="font-semibold">12,450</span>
            </div>
            <div className="flex justify-between">
              <span>Database Size</span>
              <span className="font-semibold">4.2 GB</span>
            </div>
            <div className="flex justify-between">
              <span>Active Connections</span>
              <span className="font-semibold">45</span>
            </div>
          </div>
        </Card>

        <Card title="Cache Stats">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Cache Hit Rate</span>
              <span className="font-semibold text-green-600">94.2%</span>
            </div>
            <div className="flex justify-between">
              <span>Memory Used</span>
              <span className="font-semibold">512 MB</span>
            </div>
            <div className="flex justify-between">
              <span>Keys Stored</span>
              <span className="font-semibold">8,234</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

