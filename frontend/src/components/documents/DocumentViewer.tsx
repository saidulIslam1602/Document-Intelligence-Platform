import { useState } from 'react';
import Badge from '../common/Badge';

interface Entity {
  type: string;
  value: string;
  confidence: number;
}

interface DocumentViewerProps {
  document: {
    id: string;
    filename: string;
    content?: string;
    entities?: Entity[];
    metadata?: any;
  };
}

export default function DocumentViewer({ document }: DocumentViewerProps) {
  const [activeTab, setActiveTab] = useState<'content' | 'entities' | 'metadata'>('content');

  return (
    <div className="space-y-4">
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('content')}
          className={`px-4 py-2 ${activeTab === 'content' ? 'border-b-2 border-blue-600' : ''}`}
        >
          Content
        </button>
        <button
          onClick={() => setActiveTab('entities')}
          className={`px-4 py-2 ${activeTab === 'entities' ? 'border-b-2 border-blue-600' : ''}`}
        >
          Entities ({document.entities?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('metadata')}
          className={`px-4 py-2 ${activeTab === 'metadata' ? 'border-b-2 border-blue-600' : ''}`}
        >
          Metadata
        </button>
      </div>

      {activeTab === 'content' && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <pre className="whitespace-pre-wrap text-sm">
            {document.content || 'No content available'}
          </pre>
        </div>
      )}

      {activeTab === 'entities' && (
        <div className="space-y-2">
          {document.entities?.map((entity, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div>
                <Badge variant="info">{entity.type}</Badge>
                <span className="ml-2">{entity.value}</span>
              </div>
              <span className="text-sm text-gray-500">{(entity.confidence * 100).toFixed(0)}%</span>
            </div>
          )) || <p className="text-gray-500">No entities extracted</p>}
        </div>
      )}

      {activeTab === 'metadata' && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <pre className="text-sm">
            {JSON.stringify(document.metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

