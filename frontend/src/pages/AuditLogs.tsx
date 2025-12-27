import { useState, useEffect } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Pagination from '../components/common/Pagination';

interface AuditLog {
  id: string;
  timestamp: Date;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  status: 'success' | 'failure';
  ip_address: string;
  details?: any;
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    action: 'all',
    status: 'all',
    dateFrom: '',
    dateTo: ''
  });

  useEffect(() => {
    loadLogs();
  }, [currentPage, filters]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const res = await api.get('/audit/logs', {
        params: {
          page: currentPage,
          limit: 50,
          ...filters
        }
      });

      // Mock data for demo
      const mockLogs: AuditLog[] = Array.from({ length: 50 }, (_, i) => ({
        id: `log-${currentPage}-${i}`,
        timestamp: new Date(Date.now() - i * 3600000),
        user_id: `user${i % 5}@example.com`,
        action: ['document.upload', 'document.delete', 'user.login', 'workflow.create'][i % 4],
        resource_type: ['document', 'user', 'workflow'][i % 3],
        resource_id: `res-${i}`,
        status: i % 10 === 0 ? 'failure' : 'success',
        ip_address: `192.168.1.${i % 255}`
      }));

      setLogs(res.data.logs || mockLogs);
      setTotalPages(res.data.total_pages || 10);
    } catch (error) {
      console.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action: string) => {
    if (action.includes('delete')) return 'error';
    if (action.includes('create')) return 'success';
    if (action.includes('update')) return 'warning';
    return 'info';
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Audit Logs</h1>

      <Card>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Action</label>
            <select
              value={filters.action}
              onChange={(e) => setFilters({...filters, action: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="all">All Actions</option>
              <option value="document.upload">Document Upload</option>
              <option value="document.delete">Document Delete</option>
              <option value="user.login">User Login</option>
              <option value="workflow.create">Workflow Create</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({...filters, status: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="all">All Status</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">From</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => setFilters({...filters, dateFrom: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">To</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => setFilters({...filters, dateTo: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
        </div>
      </Card>

      <Card>
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-2">Timestamp</th>
                    <th className="text-left py-3 px-2">User</th>
                    <th className="text-left py-3 px-2">Action</th>
                    <th className="text-left py-3 px-2">Resource</th>
                    <th className="text-left py-3 px-2">Status</th>
                    <th className="text-left py-3 px-2">IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map(log => (
                    <tr key={log.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-2">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 px-2 font-mono text-xs">{log.user_id}</td>
                      <td className="py-3 px-2">
                        <Badge variant={getActionColor(log.action)}>
                          {log.action}
                        </Badge>
                      </td>
                      <td className="py-3 px-2">
                        <span className="text-xs">
                          {log.resource_type}:{log.resource_id}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <Badge variant={log.status === 'success' ? 'success' : 'error'}>
                          {log.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 font-mono text-xs">{log.ip_address}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
              />
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

