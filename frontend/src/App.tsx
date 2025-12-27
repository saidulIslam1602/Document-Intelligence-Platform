import { Routes, Route, Navigate } from 'react-router-dom';
import { useState, lazy, Suspense } from 'react';
import { AppProvider } from './context/AppContext';
import Layout from './components/layout/Layout';
import LoadingSpinner from './components/common/LoadingSpinner';

// Lazy load pages for code splitting - reduces initial bundle size
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Documents = lazy(() => import('./pages/Documents'));
const BatchUpload = lazy(() => import('./pages/BatchUpload'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Chat = lazy(() => import('./pages/Chat'));
const Settings = lazy(() => import('./pages/Settings'));
const Workflows = lazy(() => import('./pages/Workflows'));
const Entities = lazy(() => import('./pages/Entities'));
const ApiKeys = lazy(() => import('./pages/ApiKeys'));
const Search = lazy(() => import('./pages/Search'));
const Admin = lazy(() => import('./pages/Admin'));
const MCPTools = lazy(() => import('./pages/MCPTools'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const ProcessingPipeline = lazy(() => import('./pages/ProcessingPipeline'));
const Webhooks = lazy(() => import('./pages/Webhooks'));

function App() {
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('token'));

  return (
    <AppProvider>
      <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><LoadingSpinner size="large" /></div>}>
        <Routes>
          <Route path="/login" element={<Login setAuth={setIsAuth} />} />
          <Route path="/register" element={<Register />} />
          
          {isAuth ? (
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="documents" element={<Documents />} />
              <Route path="batch-upload" element={<BatchUpload />} />
              <Route path="processing-pipeline" element={<ProcessingPipeline />} />
              <Route path="workflows" element={<Workflows />} />
              <Route path="entities" element={<Entities />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="chat" element={<Chat />} />
              <Route path="search" element={<Search />} />
              <Route path="mcp-tools" element={<MCPTools />} />
              <Route path="api-keys" element={<ApiKeys />} />
              <Route path="webhooks" element={<Webhooks />} />
              <Route path="audit-logs" element={<AuditLogs />} />
              <Route path="admin" element={<Admin />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          ) : (
            <Route path="*" element={<Navigate to="/login" />} />
          )}
        </Routes>
      </Suspense>
    </AppProvider>
  );
}

export default App;

