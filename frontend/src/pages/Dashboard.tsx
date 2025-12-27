import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import MetricCard from '../components/dashboard/MetricCard';
import Card from '../components/common/Card';
import Chart from '../components/analytics/Chart';
import Button from '../components/common/Button';
import { useAuth } from '../hooks/useAuth';
import { hasPermission } from '../utils/roleUtils';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [recentDocs, setRecentDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const canViewMetrics = user ? hasPermission(user.role, 'viewSystemMetrics') : false;
  const isUser = user?.role === 'user';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [metricsRes, docsRes] = await Promise.all([
        api.get('/analytics/automation-metrics'),
        api.get('/documents?limit=5')
      ]);
      setMetrics(metricsRes.data);
      setRecentDocs(docsRes.data.documents || []);
    } catch (error) {
      console.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Loading...</div>;

  const processingTrend = [
    { label: 'Mon', value: 45 },
    { label: 'Tue', value: 52 },
    { label: 'Wed', value: 48 },
    { label: 'Thu', value: 65 },
    { label: 'Fri', value: 58 },
    { label: 'Sat', value: 42 },
    { label: 'Sun', value: 38 },
  ];

  return (
    <div className="space-y-6">
      {isUser && (
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
          <h2 className="text-2xl font-bold mb-2">Welcome to Document Intelligence</h2>
          <p className="text-blue-100 mb-4">
            Upload your invoices and let our AI extract, analyze, and organize your data automatically.
          </p>
          <div className="flex gap-4">
            <Button onClick={() => navigate('/documents')} variant="secondary" className="bg-white text-blue-600 hover:bg-gray-100">
              Upload Documents
            </Button>
            <Button onClick={() => navigate('/chat')} variant="secondary" className="bg-blue-700 hover:bg-blue-800">
              Ask AI Assistant
            </Button>
          </div>
        </div>
      )}
      
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">
            {isUser ? 'My Dashboard' : 'System Dashboard'}
          </h1>
          <p className="text-gray-600 text-sm mt-1">
            {isUser ? 'View your documents and activity' : 'Monitor platform performance and analytics'}
          </p>
        </div>
        {!isUser && (
          <Button onClick={() => navigate('/documents')}>
            Upload Document
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="My Documents" 
          value={recentDocs.length}
          change={0}
          icon="📄"
        />
        <MetricCard 
          title="Completed" 
          value={recentDocs.filter(d => d.status === 'completed').length}
          change={0}
          icon="✅"
        />
        {canViewMetrics && (
          <>
            <MetricCard 
              title="Automation Rate" 
              value={`${metrics?.automationRate || 0}%`}
              change={12}
              icon="🤖"
            />
            <MetricCard 
              title="API Calls Today" 
              value="2,847"
              change={15}
              icon="📊"
            />
          </>
        )}
        {!canViewMetrics && (
          <>
            <MetricCard 
              title="Processing" 
              value={recentDocs.filter(d => d.status === 'processing').length}
              change={0}
              icon="⏳"
            />
            <MetricCard 
              title="Upload" 
              value="Upload New"
              icon="⬆️"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {canViewMetrics && (
          <Card title="Processing Trend">
            <Chart data={processingTrend} />
          </Card>
        )}

        <Card title="Recent Documents">
          <div className="space-y-3">
            {recentDocs.map((doc) => (
              <div key={doc.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">{doc.filename}</p>
                  <p className="text-sm text-gray-500">{new Date(doc.uploadedAt).toLocaleString()}</p>
                </div>
                <span className="text-sm text-green-600">{doc.status}</span>
              </div>
            ))}
            {recentDocs.length === 0 && (
              <p className="text-gray-500 text-center py-4">No documents yet</p>
            )}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="System Health">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span>API Gateway</span>
              <span className="text-green-600">●  Online</span>
            </div>
            <div className="flex justify-between">
              <span>Document Processor</span>
              <span className="text-green-600">●  Online</span>
            </div>
            <div className="flex justify-between">
              <span>AI Engine</span>
              <span className="text-green-600">●  Online</span>
            </div>
            <div className="flex justify-between">
              <span>Database</span>
              <span className="text-green-600">●  Online</span>
            </div>
          </div>
        </Card>

        <Card title="Quick Actions" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-3">
            <Button onClick={() => navigate('/documents')} variant="primary">
              Upload Document
            </Button>
            <Button onClick={() => navigate('/analytics')} variant="secondary">
              View Analytics
            </Button>
            <Button onClick={() => navigate('/chat')} variant="secondary">
              Start AI Chat
            </Button>
            <Button onClick={() => navigate('/workflows')} variant="secondary">
              Create Workflow
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

