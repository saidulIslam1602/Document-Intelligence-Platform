export interface User {
  id: string;
  email: string;
  username: string;
  role: 'admin' | 'user' | 'developer';
  status: 'active' | 'inactive';
}

export interface Document {
  id: string;
  filename: string;
  status: 'completed' | 'processing' | 'failed' | 'pending';
  uploadedAt: string;
  fileSize?: number;
  fileType?: string;
  extractedEntities?: number;
  content?: string;
  metadata?: Record<string, any>;
}

export interface Entity {
  id: string;
  type: string;
  value: string;
  confidence: number;
  documentId: string;
  documentName: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'paused' | 'draft';
  triggers: string[];
  actions: string[];
  runsToday: number;
  createdAt: string;
}

export interface Metrics {
  automationRate: number;
  totalProcessed: number;
  successRate?: number;
  avgProcessingTime?: number;
}

export interface ApiKey {
  id: string;
  name: string;
  key: string;
  created: Date;
  lastUsed?: Date;
  status: 'active' | 'revoked';
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface SystemHealth {
  apiGateway: string;
  documentProcessor: string;
  aiEngine: string;
  database: string;
  redis: string;
}

