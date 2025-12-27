import { useEffect, useState } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import Chart from '../components/analytics/Chart';
import MetricCard from '../components/dashboard/MetricCard';

export default function Analytics() {
  const [data, setData] = useState<any>(null);
  const [timeRange, setTimeRange] = useState<'day' | 'week' | 'month'>('week');

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const loadAnalytics = async () => {
    try {
      const res = await api.get(`/analytics/automation-metrics?range=${timeRange}`);
      setData(res.data);
    } catch (error) {
      console.error('Failed to load analytics');
    }
  };

  const processingByType = [
    { label: 'PDF', value: 145 },
    { label: 'Word', value: 89 },
    { label: 'Image', value: 62 },
    { label: 'Text', value: 34 },
  ];

  const extractionAccuracy = [
    { label: 'Invoices', value: 98 },
    { label: 'Contracts', value: 95 },
    { label: 'Reports', value: 92 },
    { label: 'Forms', value: 88 },
  ];

  const processingTime = [
    { label: 'Mon', value: 125 },
    { label: 'Tue', value: 142 },
    { label: 'Wed', value: 138 },
    { label: 'Thu', value: 165 },
    { label: 'Fri', value: 155 },
    { label: 'Sat', value: 98 },
    { label: 'Sun', value: 87 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Analytics & Insights</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setTimeRange('day')}
            className={`px-4 py-2 rounded ${timeRange === 'day' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Day
          </button>
          <button
            onClick={() => setTimeRange('week')}
            className={`px-4 py-2 rounded ${timeRange === 'week' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Week
          </button>
          <button
            onClick={() => setTimeRange('month')}
            className={`px-4 py-2 rounded ${timeRange === 'month' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            Month
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Automation Rate" 
          value={`${data?.automationRate || 0}%`}
          change={5}
        />
        <MetricCard 
          title="Total Processed" 
          value={data?.totalProcessed || 0}
          change={12}
        />
        <MetricCard 
          title="Avg Processing Time" 
          value="2.3s"
          change={-8}
        />
        <MetricCard 
          title="Success Rate" 
          value="97.5%"
          change={3}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Documents by Type">
          <Chart data={processingByType} />
        </Card>

        <Card title="Extraction Accuracy (%)">
          <Chart data={extractionAccuracy} />
        </Card>
      </div>

      <Card title="Processing Volume (Last 7 Days)">
        <Chart data={processingTime} />
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Top Entities Extracted">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Names</span>
              <span className="font-semibold">1,247</span>
            </div>
            <div className="flex justify-between">
              <span>Dates</span>
              <span className="font-semibold">892</span>
            </div>
            <div className="flex justify-between">
              <span>Amounts</span>
              <span className="font-semibold">756</span>
            </div>
            <div className="flex justify-between">
              <span>Organizations</span>
              <span className="font-semibold">543</span>
            </div>
          </div>
        </Card>

        <Card title="Processing Errors">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Format Unsupported</span>
              <span className="text-red-600">12</span>
            </div>
            <div className="flex justify-between">
              <span>OCR Failed</span>
              <span className="text-red-600">8</span>
            </div>
            <div className="flex justify-between">
              <span>Timeout</span>
              <span className="text-red-600">5</span>
            </div>
            <div className="flex justify-between">
              <span>Other</span>
              <span className="text-red-600">3</span>
            </div>
          </div>
        </Card>

        <Card title="Cost Savings">
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-500">Time Saved</p>
              <p className="text-2xl font-bold">245 hrs</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Cost Reduced</p>
              <p className="text-2xl font-bold text-green-600">$12,450</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">ROI</p>
              <p className="text-2xl font-bold text-blue-600">340%</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

