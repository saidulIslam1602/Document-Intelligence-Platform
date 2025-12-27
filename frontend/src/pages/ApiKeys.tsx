import { useState } from 'react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Badge from '../components/common/Badge';

interface ApiKey {
  id: string;
  name: string;
  key: string;
  created: Date;
  lastUsed?: Date;
  status: 'active' | 'revoked';
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([
    {
      id: '1',
      name: 'Production API Key',
      key: 'sk_prod_abc123...xyz789',
      created: new Date('2024-01-01'),
      lastUsed: new Date('2024-01-15'),
      status: 'active'
    }
  ]);
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const createKey = () => {
    const key: ApiKey = {
      id: String(keys.length + 1),
      name: newKeyName,
      key: `sk_${Math.random().toString(36).substring(2, 15)}`,
      created: new Date(),
      status: 'active'
    };
    setKeys([...keys, key]);
    setCreatedKey(key.key);
    setNewKeyName('');
  };

  const revokeKey = (id: string) => {
    if (confirm('Are you sure you want to revoke this API key?')) {
      setKeys(keys.map(k => k.id === id ? {...k, status: 'revoked'} : k));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">API Keys</h1>
        <Button onClick={() => setShowCreate(true)}>
          Create API Key
        </Button>
      </div>

      <Card>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-blue-800">
            <strong>Important:</strong> Keep your API keys secure. Never share them publicly or commit them to version control.
          </p>
        </div>

        <div className="space-y-4">
          {keys.map(key => (
            <div key={key.id} className="flex justify-between items-start p-4 border rounded-lg">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-semibold">{key.name}</h3>
                  <Badge variant={key.status === 'active' ? 'success' : 'error'}>
                    {key.status}
                  </Badge>
                </div>
                
                <p className="font-mono text-sm bg-gray-100 px-3 py-2 rounded mb-2">
                  {key.key}
                </p>
                
                <div className="text-sm text-gray-600">
                  <p>Created: {key.created.toLocaleDateString()}</p>
                  {key.lastUsed && <p>Last used: {key.lastUsed.toLocaleDateString()}</p>}
                </div>
              </div>
              
              {key.status === 'active' && (
                <Button variant="danger" onClick={() => revokeKey(key.id)}>
                  Revoke
                </Button>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Modal isOpen={showCreate} onClose={() => {setShowCreate(false); setCreatedKey(null);}} title="Create API Key">
        {!createdKey ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Key Name</label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="e.g., Production API Key"
              />
            </div>
            
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button onClick={createKey} disabled={!newKeyName}>
                Create
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-yellow-800">
                <strong>Important:</strong> Copy this key now. You won't be able to see it again!
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Your API Key</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={createdKey}
                  readOnly
                  className="flex-1 px-3 py-2 border rounded-lg font-mono"
                />
                <Button onClick={() => navigator.clipboard.writeText(createdKey)}>
                  Copy
                </Button>
              </div>
            </div>
            
            <Button onClick={() => {setShowCreate(false); setCreatedKey(null);}} className="w-full">
              Done
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

