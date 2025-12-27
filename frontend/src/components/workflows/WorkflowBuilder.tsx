import { useState } from 'react';
import Button from '../common/Button';
import Card from '../common/Card';

export default function WorkflowBuilder() {
  const [triggers, setTriggers] = useState<string[]>([]);
  const [actions, setActions] = useState<string[]>([]);

  const availableTriggers = [
    'Document Upload',
    'Document Type Detected',
    'Entity Extracted',
    'Scheduled Time',
    'API Call',
    'Webhook Received'
  ];

  const availableActions = [
    'Extract Entities',
    'Classify Document',
    'Send Email',
    'Call Webhook',
    'Store in Database',
    'Generate Report',
    'OCR Processing',
    'AI Analysis'
  ];

  const addTrigger = (trigger: string) => {
    if (!triggers.includes(trigger)) {
      setTriggers([...triggers, trigger]);
    }
  };

  const addAction = (action: string) => {
    setActions([...actions, action]);
  };

  const removeTrigger = (index: number) => {
    setTriggers(triggers.filter((_, i) => i !== index));
  };

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      <Card title="Workflow Triggers">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {availableTriggers.map(trigger => (
              <button
                key={trigger}
                onClick={() => addTrigger(trigger)}
                className="px-3 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 text-sm"
              >
                + {trigger}
              </button>
            ))}
          </div>

          {triggers.length > 0 && (
            <div className="space-y-2 mt-4">
              <p className="font-medium text-sm">Selected Triggers:</p>
              {triggers.map((trigger, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-green-50 rounded">
                  <span className="text-green-800">{trigger}</span>
                  <button
                    onClick={() => removeTrigger(idx)}
                    className="text-red-600 hover:text-red-800"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <div className="text-center text-2xl">↓</div>

      <Card title="Workflow Actions">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {availableActions.map(action => (
              <button
                key={action}
                onClick={() => addAction(action)}
                className="px-3 py-1 bg-purple-50 text-purple-600 rounded hover:bg-purple-100 text-sm"
              >
                + {action}
              </button>
            ))}
          </div>

          {actions.length > 0 && (
            <div className="space-y-2 mt-4">
              <p className="font-medium text-sm">Action Sequence:</p>
              {actions.map((action, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 bg-purple-50 rounded">
                  <span className="text-purple-800 font-medium">{idx + 1}.</span>
                  <span className="flex-1 text-purple-800">{action}</span>
                  <button
                    onClick={() => removeAction(idx)}
                    className="text-red-600 hover:text-red-800"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <div className="flex gap-3">
        <Button variant="primary" disabled={triggers.length === 0 || actions.length === 0}>
          Save Workflow
        </Button>
        <Button variant="secondary">
          Test Workflow
        </Button>
      </div>
    </div>
  );
}

