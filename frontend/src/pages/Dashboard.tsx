import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import MetricCard from '../components/dashboard/MetricCard';
import Card from '../components/common/Card';
import Chart from '../components/analytics/Chart';
import Button from '../components/common/Button';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [recentDocs, setRecentDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

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
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Button onClick={() => navigate('/documents')}>
          Upload Document
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Automation Rate" 
          value={`${metrics?.automationRate || 0}%`}
          change={12}
          icon="🤖"
        />
        <MetricCard 
          title="Documents Processed" 
          value={metrics?.totalProcessed || 0}
          change={8}
          icon="📄"
        />
        <MetricCard 
          title="Active Workflows" 
          value="12"
          change={-3}
          icon="⚙️"
        />
        <MetricCard 
          title="API Calls Today" 
          value="2,847"
          change={15}
          icon="📊"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Processing Trend">
          <Chart data={processingTrend} />
        </Card>

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

