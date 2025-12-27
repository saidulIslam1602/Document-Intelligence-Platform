import { useState, useEffect } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Badge from '../components/common/Badge';

interface MCPTool {
  name: string;
  description: string;
  input_schema: any;
  category?: string;
}

export default function MCPTools() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [toolInput, setToolInput] = useState<string>('{}');
  const [toolResult, setToolResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const res = await api.get('/mcp/tools');
      setTools(res.data.tools || []);
    } catch (error) {
      console.error('Failed to load MCP tools');
    } finally {
      setLoading(false);
    }
  };

  const executeTool = async () => {
    if (!selectedTool) return;

    setExecuting(true);
    setToolResult(null);

    try {
      const input = JSON.parse(toolInput);
      const res = await api.post('/mcp/execute-tool', {
        tool_name: selectedTool.name,
        arguments: input
      });
      setToolResult(res.data);
    } catch (error: any) {
      setToolResult({ error: error.response?.data?.message || 'Execution failed' });
    } finally {
      setExecuting(false);
    }
  };

  const toolsByCategory = tools.reduce((acc, tool) => {
    const category = tool.category || 'General';
    if (!acc[category]) acc[category] = [];
    acc[category].push(tool);
    return acc;
  }, {} as Record<string, MCPTool[]>);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">MCP Tools</h1>
        <Button onClick={loadTools} variant="secondary">
          Refresh
        </Button>
      </div>

      {loading ? (
        <Card>
          <div className="flex justify-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
          </div>
        </Card>
      ) : (
        <>
          <Card>
            <p className="text-gray-600 mb-4">
              Model Context Protocol (MCP) tools provide structured capabilities for AI agents and clients.
            </p>
            <div className="flex gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">{tools.length}</p>
                <p className="text-sm text-gray-500">Total Tools</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">{Object.keys(toolsByCategory).length}</p>
                <p className="text-sm text-gray-500">Categories</p>
              </div>
            </div>
          </Card>

          {Object.entries(toolsByCategory).map(([category, categoryTools]) => (
            <Card key={category} title={category}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {categoryTools.map(tool => (
                  <div
                    key={tool.name}
                    onClick={() => setSelectedTool(tool)}
                    className="p-4 border rounded-lg hover:border-blue-500 hover:shadow cursor-pointer transition-all"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold">{tool.name}</h3>
                      <Badge variant="info">Tool</Badge>
                    </div>
                    <p className="text-sm text-gray-600">{tool.description}</p>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </>
      )}

      <Modal
        isOpen={!!selectedTool}
        onClose={() => {
          setSelectedTool(null);
          setToolResult(null);
          setToolInput('{}');
        }}
        title={selectedTool?.name || 'Tool Details'}
      >
        {selectedTool && (
          <div className="space-y-4">
            <div>
              <p className="text-gray-600">{selectedTool.description}</p>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Input Schema</h4>
              <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto">
                {JSON.stringify(selectedTool.input_schema, null, 2)}
              </pre>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Tool Input (JSON)</h4>
              <textarea
                value={toolInput}
                onChange={(e) => setToolInput(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                rows={6}
                placeholder='{"document_id": "123"}'
              />
            </div>

            <Button onClick={executeTool} disabled={executing} className="w-full">
              {executing ? 'Executing...' : 'Execute Tool'}
            </Button>

            {toolResult && (
              <div>
                <h4 className="font-semibold mb-2">Result</h4>
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto max-h-64">
                  {JSON.stringify(toolResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

