import { useState, useEffect } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import { useWebSocket } from '../hooks/useWebSocket';

interface PipelineStage {
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  duration?: number;
  message?: string;
}

interface ProcessingJob {
  document_id: string;
  filename: string;
  stages: PipelineStage[];
  overall_status: string;
  start_time: Date;
  completion_time?: Date;
}

export default function ProcessingPipeline() {
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const wsUrl = import.meta.env.VITE_WS_URL?.replace('http', 'ws') + '/ws/processing';
  const { lastMessage } = useWebSocket(wsUrl);

  useEffect(() => {
    if (lastMessage) {
      // Update jobs based on WebSocket messages
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage]);

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    try {
      const res = await api.get('/processing/jobs?limit=10');
      setJobs(res.data.jobs || getMockJobs());
    } catch (error) {
      setJobs(getMockJobs());
    }
  };

  const handleWebSocketMessage = (message: any) => {
    if (message.type === 'processing_update') {
      setJobs(prev => prev.map(job =>
        job.document_id === message.data.document_id
          ? { ...job, ...message.data }
          : job
      ));
    }
  };

  const getMockJobs = (): ProcessingJob[] => [
    {
      document_id: 'doc-1',
      filename: 'invoice_001.pdf',
      overall_status: 'processing',
      start_time: new Date(),
      stages: [
        { name: 'Upload', status: 'completed', duration: 0.5 },
        { name: 'OCR', status: 'processing', message: 'Extracting text...' },
        { name: 'Classification', status: 'pending' },
        { name: 'Extraction', status: 'pending' },
        { name: 'Validation', status: 'pending' }
      ]
    }
  ];

  const getStageIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✓';
      case 'processing': return '⟳';
      case 'failed': return '✕';
      default: return '○';
    }
  };

  const getStageColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'processing': return 'text-blue-600 animate-pulse';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Processing Pipeline</h1>

      <Card>
        <p className="text-gray-600">
          Real-time visualization of document processing stages. Monitor OCR, classification, extraction, and validation.
        </p>
      </Card>

      <div className="space-y-4">
        {jobs.map(job => (
          <Card key={job.document_id}>
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg">{job.filename}</h3>
                  <p className="text-sm text-gray-500">ID: {job.document_id}</p>
                  <p className="text-sm text-gray-500">
                    Started: {new Date(job.start_time).toLocaleString()}
                  </p>
                </div>
                <Badge variant={
                  job.overall_status === 'completed' ? 'success' :
                  job.overall_status === 'processing' ? 'warning' : 'info'
                }>
                  {job.overall_status}
                </Badge>
              </div>

              <div className="relative">
                {/* Progress Line */}
                <div className="absolute top-5 left-0 right-0 h-0.5 bg-gray-200">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{
                      width: `${(job.stages.filter(s => s.status === 'completed').length / job.stages.length) * 100}%`
                    }}
                  />
                </div>

                {/* Stages */}
                <div className="relative flex justify-between">
                  {job.stages.map((stage, idx) => (
                    <div key={idx} className="flex flex-col items-center">
                      <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center bg-white ${
                        stage.status === 'completed' ? 'border-green-600' :
                        stage.status === 'processing' ? 'border-blue-600' :
                        stage.status === 'failed' ? 'border-red-600' : 'border-gray-300'
                      }`}>
                        <span className={`text-xl ${getStageColor(stage.status)}`}>
                          {getStageIcon(stage.status)}
                        </span>
                      </div>
                      <p className="text-sm font-medium mt-2">{stage.name}</p>
                      {stage.duration && (
                        <p className="text-xs text-gray-500">{stage.duration}s</p>
                      )}
                      {stage.message && (
                        <p className="text-xs text-blue-600 mt-1">{stage.message}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

