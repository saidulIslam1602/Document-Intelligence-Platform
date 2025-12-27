import { useState } from 'react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Badge from '../components/common/Badge';

interface Webhook {
  id: string;
  url: string;
  events: string[];
  status: 'active' | 'inactive';
  secret: string;
  created_at: Date;
  last_triggered?: Date;
}

export default function Webhooks() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([
    {
      id: '1',
      url: 'https://api.example.com/webhooks/document-processed',
      events: ['document.processed', 'document.failed'],
      status: 'active',
      secret: 'whsec_abc123...',
      created_at: new Date('2024-01-01'),
      last_triggered: new Date()
    }
  ]);
  const [showCreate, setShowCreate] = useState(false);
  const [newWebhook, setNewWebhook] = useState({
    url: '',
    events: [] as string[]
  });

  const availableEvents = [
    'document.uploaded',
    'document.processed',
    'document.failed',
    'workflow.completed',
    'extraction.complete'
  ];

  const createWebhook = () => {
    const webhook: Webhook = {
      id: String(webhooks.length + 1),
      ...newWebhook,
      status: 'active',
      secret: `whsec_${Math.random().toString(36).substring(2)}`,
      created_at: new Date()
    };
    setWebhooks([...webhooks, webhook]);
    setShowCreate(false);
    setNewWebhook({ url: '', events: [] });
  };

  const toggleEvent = (event: string) => {
    setNewWebhook({
      ...newWebhook,
      events: newWebhook.events.includes(event)
        ? newWebhook.events.filter(e => e !== event)
        : [...newWebhook.events, event]
    });
  };

  const deleteWebhook = (id: string) => {
    if (confirm('Delete this webhook?')) {
      setWebhooks(webhooks.filter(w => w.id !== id));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Webhooks</h1>
        <Button onClick={() => setShowCreate(true)}>
          Create Webhook
        </Button>
      </div>

      <Card>
        <p className="text-gray-600">
          Configure webhooks to receive real-time notifications when events occur in your account.
        </p>
      </Card>

      <div className="space-y-4">
        {webhooks.map(webhook => (
          <Card key={webhook.id}>
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold">{webhook.url}</h3>
                    <Badge variant={webhook.status === 'active' ? 'success' : 'error'}>
                      {webhook.status}
                    </Badge>
                  </div>

                  <div className="space-y-2">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Events:</p>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {webhook.events.map(event => (
                          <span key={event} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                            {event}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="text-sm font-medium text-gray-600">Signing Secret:</p>
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">{webhook.secret}</code>
                    </div>

                    <div className="flex gap-6 text-sm text-gray-500">
                      <span>Created: {webhook.created_at.toLocaleDateString()}</span>
                      {webhook.last_triggered && (
                        <span>Last triggered: {webhook.last_triggered.toLocaleString()}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button variant="secondary" className="text-sm">
                    Test
                  </Button>
                  <Button variant="danger" onClick={() => deleteWebhook(webhook.id)} className="text-sm">
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        ))}

        {webhooks.length === 0 && (
          <Card>
            <p className="text-center text-gray-500 py-8">
              No webhooks configured. Create one to get started.
            </p>
          </Card>
        )}
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Webhook">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Webhook URL</label>
            <input
              type="url"
              value={newWebhook.url}
              onChange={(e) => setNewWebhook({...newWebhook, url: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="https://your-domain.com/webhook"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Events to Subscribe</label>
            <div className="space-y-2">
              {availableEvents.map(event => (
                <label key={event} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newWebhook.events.includes(event)}
                    onChange={() => toggleEvent(event)}
                    className="rounded"
                  />
                  <span>{event}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button onClick={createWebhook} disabled={!newWebhook.url || newWebhook.events.length === 0}>
              Create
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

