import { useState } from 'react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Badge from '../components/common/Badge';

interface Workflow {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'draft';
  triggers: string[];
  actions: string[];
  runsToday: number;
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([
    {
      id: '1',
      name: 'Invoice Processing',
      status: 'active',
      triggers: ['Document Upload', 'Type: Invoice'],
      actions: ['Extract Data', 'Validate', 'Store in Database'],
      runsToday: 45
    },
    {
      id: '2',
      name: 'Contract Analysis',
      status: 'active',
      triggers: ['Document Upload', 'Type: Contract'],
      actions: ['Extract Clauses', 'Risk Analysis', 'Generate Summary'],
      runsToday: 12
    }
  ]);
  const [showCreate, setShowCreate] = useState(false);
  const [newWorkflow, setNewWorkflow] = useState({ name: '', description: '' });

  const createWorkflow = () => {
    const workflow: Workflow = {
      id: String(workflows.length + 1),
      name: newWorkflow.name,
      status: 'draft',
      triggers: [],
      actions: [],
      runsToday: 0
    };
    setWorkflows([...workflows, workflow]);
    setShowCreate(false);
    setNewWorkflow({ name: '', description: '' });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Workflow Automation</h1>
        <Button onClick={() => setShowCreate(true)}>
          Create Workflow
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <p className="text-sm text-gray-500">Active Workflows</p>
          <p className="text-3xl font-bold">{workflows.filter(w => w.status === 'active').length}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Total Runs Today</p>
          <p className="text-3xl font-bold">{workflows.reduce((sum, w) => sum + w.runsToday, 0)}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Success Rate</p>
          <p className="text-3xl font-bold text-green-600">98.5%</p>
        </Card>
      </div>

      <div className="space-y-4">
        {workflows.map(workflow => (
          <Card key={workflow.id}>
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold">{workflow.name}</h3>
                  <Badge variant={workflow.status === 'active' ? 'success' : workflow.status === 'paused' ? 'warning' : 'info'}>
                    {workflow.status}
                  </Badge>
                </div>
                
                <div className="mb-3">
                  <p className="text-sm font-medium text-gray-600 mb-1">Triggers:</p>
                  <div className="flex flex-wrap gap-2">
                    {workflow.triggers.map((trigger, idx) => (
                      <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        {trigger}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="mb-3">
                  <p className="text-sm font-medium text-gray-600 mb-1">Actions:</p>
                  <div className="flex flex-wrap gap-2">
                    {workflow.actions.map((action, idx) => (
                      <span key={idx} className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                        {action}
                      </span>
                    ))}
                  </div>
                </div>
                
                <p className="text-sm text-gray-500">
                  Executed {workflow.runsToday} times today
                </p>
              </div>
              
              <div className="flex gap-2">
                <Button variant="secondary" className="text-sm">
                  Edit
                </Button>
                <Button 
                  variant={workflow.status === 'active' ? 'secondary' : 'primary'}
                  className="text-sm"
                >
                  {workflow.status === 'active' ? 'Pause' : 'Activate'}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Workflow">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Workflow Name</label>
            <input
              type="text"
              value={newWorkflow.name}
              onChange={(e) => setNewWorkflow({...newWorkflow, name: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="e.g., Invoice Processing"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={newWorkflow.description}
              onChange={(e) => setNewWorkflow({...newWorkflow, description: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
              rows={3}
              placeholder="Describe what this workflow does..."
            />
          </div>
          
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button onClick={createWorkflow} disabled={!newWorkflow.name}>
              Create
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

