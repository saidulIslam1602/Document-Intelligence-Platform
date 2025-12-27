import { Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import { AppProvider } from './context/AppContext';
import Layout from './components/layout/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import BatchUpload from './pages/BatchUpload';
import Analytics from './pages/Analytics';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Workflows from './pages/Workflows';
import Entities from './pages/Entities';
import ApiKeys from './pages/ApiKeys';
import Search from './pages/Search';
import Admin from './pages/Admin';
import MCPTools from './pages/MCPTools';
import AuditLogs from './pages/AuditLogs';
import ProcessingPipeline from './pages/ProcessingPipeline';
import Webhooks from './pages/Webhooks';

function App() {
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('token'));

  return (
    <AppProvider>
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
    </AppProvider>
  );
}

export default App;

