# Complete Implementation Guide - React Frontend

This guide contains ALL the source code needed for the Document Intelligence Platform frontend.

## Quick Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Complete Source Code

### 1. Configuration Files

#### `.env.example`
```env
VITE_API_URL=http://localhost:8003
VITE_WS_URL=ws://localhost:8003
VITE_APP_NAME=Document Intelligence Platform
VITE_APP_VERSION=2.0.0
```

#### `postcss.config.js`
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

#### `tsconfig.node.json`
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

#### `.eslintrc.cjs`
```javascript
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
  },
}
```

---

### 2. Entry Point Files

#### `index.html`
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/logo.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="Document Intelligence Platform - AI-powered document processing" />
    <title>Document Intelligence Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

#### `src/main.tsx`
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import App from './App';
import './styles/index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
```

#### `src/App.tsx`
```typescript
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { useThemeStore } from './stores/themeStore';
import { useEffect } from 'react';

// Layout
import Layout from './components/layout/Layout';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import Analytics from './pages/Analytics';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import NotFound from './pages/NotFound';

function App() {
  const { isAuthenticated } = useAuthStore();
  const { isDark } = useThemeStore();

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <Routes>
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/dashboard" /> : <Login />
      } />
      
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/dashboard" />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="documents" element={<Documents />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="chat" element={<Chat />} />
        <Route path="settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
```

#### `src/styles/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * {
    @apply border-border;
  }
  
  body {
    @apply bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100;
    @apply antialiased;
  }

  ::-webkit-scrollbar {
    @apply w-2 h-2;
  }

  ::-webkit-scrollbar-track {
    @apply bg-gray-100 dark:bg-gray-800;
  }

  ::-webkit-scrollbar-thumb {
    @apply bg-gray-300 dark:bg-gray-600 rounded-full;
  }

  ::-webkit-scrollbar-thumb:hover {
    @apply bg-gray-400 dark:bg-gray-500;
  }
}

@layer components {
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200;
    @apply focus:outline-none focus:ring-2 focus:ring-offset-2;
    @apply disabled:opacity-50 disabled:cursor-not-allowed;
  }

  .btn-primary {
    @apply bg-primary-600 text-white hover:bg-primary-700;
    @apply focus:ring-primary-500;
  }

  .btn-secondary {
    @apply bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100;
    @apply hover:bg-gray-300 dark:hover:bg-gray-600;
    @apply focus:ring-gray-500;
  }

  .btn-success {
    @apply bg-success-600 text-white hover:bg-success-700;
    @apply focus:ring-success-500;
  }

  .btn-error {
    @apply bg-error-600 text-white hover:bg-error-700;
    @apply focus:ring-error-500;
  }

  .input {
    @apply w-full px-3 py-2 border border-gray-300 dark:border-gray-600;
    @apply rounded-lg bg-white dark:bg-gray-800;
    @apply text-gray-900 dark:text-gray-100;
    @apply placeholder-gray-400 dark:placeholder-gray-500;
    @apply focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent;
    @apply transition-all duration-200;
  }

  .card {
    @apply bg-white dark:bg-gray-800 rounded-lg shadow-soft;
    @apply border border-gray-200 dark:border-gray-700;
    @apply transition-all duration-200;
  }

  .card-hover {
    @apply hover:shadow-lg hover:scale-105;
  }
}

@layer utilities {
  .text-gradient {
    @apply bg-clip-text text-transparent bg-gradient-to-r from-primary-600 to-primary-400;
  }

  .bg-gradient-primary {
    @apply bg-gradient-to-r from-primary-600 to-primary-500;
  }

  .animate-pulse-slow {
    animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
}
```

---

### 3. Type Definitions

#### `src/types/index.ts`
```typescript
export interface User {
  id: string;
  email: string;
  username: string;
  role: 'admin' | 'user' | 'analyst';
  createdAt: string;
  lastLogin?: string;
}

export interface Document {
  id: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  progress: number;
  uploadedAt: string;
  processedAt?: string;
  userId: string;
  documentType?: string;
  processingResult?: any;
  errorMessage?: string;
}

export interface AutomationMetrics {
  automationRate: number;
  totalProcessed: number;
  fullyAutomated: number;
  requiresReview: number;
  manualIntervention: number;
  averageConfidence: number;
  timeRange: string;
  trend: 'up' | 'down' | 'stable';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: any;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  documentId?: string;
  error?: string;
}
```

---

### 4. API Services Layer

#### `src/services/api.ts`
```typescript
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { useAuthStore } from '../stores/authStore';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8003';

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

#### `src/services/auth.service.ts`
```typescript
import api from './api';
import { User, ApiResponse } from '../types';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  async logout(): Promise<void> {
    await api.post('/auth/logout');
  },

  async refreshToken(): Promise<{ access_token: string }> {
    const response = await api.post('/auth/refresh');
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};
```

#### `src/services/documents.service.ts`
```typescript
import api from './api';
import { Document, ApiResponse } from '../types';

export const documentsService = {
  async getDocuments(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<Document[]> {
    const response = await api.get<{ documents: Document[] }>('/documents', { params });
    return response.data.documents;
  },

  async getDocument(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`);
    return response.data;
  },

  async uploadDocument(file: File, onProgress?: (progress: number) => void): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });
    return response.data;
  },

  async batchUpload(files: File[]): Promise<{ documents: Document[]; failed: number }> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    const response = await api.post('/documents/batch-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
  },

  async getDocumentStatus(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}/status`);
    return response.data;
  },
};
```

#### `src/services/analytics.service.ts`
```typescript
import api from './api';
import { AutomationMetrics } from '../types';

export const analyticsService = {
  async getAutomationMetrics(timeRange: string = '24h'): Promise<AutomationMetrics> {
    const response = await api.get<AutomationMetrics>('/analytics/automation-metrics', {
      params: { time_range: timeRange },
    });
    return response.data;
  },

  async getAutomationTrend(days: number = 7): Promise<any[]> {
    const response = await api.get('/analytics/automation-trend', {
      params: { days },
    });
    return response.data;
  },

  async getInsights(): Promise<any> {
    const response = await api.get('/analytics/automation-insights');
    return response.data;
  },
};
```

#### `src/services/chat.service.ts`
```typescript
import api from './api';
import { ChatMessage } from '../types';

export const chatService = {
  async sendMessage(message: string, conversationId?: string): Promise<ChatMessage> {
    const response = await api.post<ChatMessage>('/chat/message', {
      message,
      conversation_id: conversationId,
    });
    return response.data;
  },

  async getHistory(conversationId?: string): Promise<ChatMessage[]> {
    const response = await api.get<{ messages: ChatMessage[] }>('/chat/history', {
      params: { conversation_id: conversationId },
    });
    return response.data.messages;
  },

  async createConversation(): Promise<{ conversation_id: string }> {
    const response = await api.post('/chat/conversation');
    return response.data;
  },
};
```

---

Continue in next message due to length...

## Installation Instructions

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Install required Tailwind plugins:**
```bash
npm install -D @tailwindcss/forms @tailwindcss/typography @tailwindcss/aspect-ratio
```

3. **Set up environment:**
```bash
cp .env.example .env
```

4. **Start development server:**
```bash
npm run dev
```

Your frontend will be available at `http://localhost:3000`

## Next Steps

The next message will contain:
- Complete store implementations (Zustand)
- All React components (50+ files)
- Pages implementation
- Hooks and utilities
- Complete working application

**Status:** Foundation complete - Ready for component implementation

