import Card from '../components/common/Card';

export default function About() {
  const capabilities = [
    {
      icon: '🧠',
      title: 'Fine-Tuning',
      description: 'Custom GPT-4/3.5 models trained on your document types for superior accuracy',
      features: ['Custom model training', 'Industry-specific fine-tuning', 'Continuous improvement']
    },
    {
      icon: '🔗',
      title: 'LangChain Orchestration',
      description: 'Multi-agent AI workflows for complex document processing',
      features: ['Sequential chains', 'Multi-agent collaboration', 'Intelligent reasoning']
    },
    {
      icon: '🎯',
      title: 'Intelligent Routing',
      description: 'Automatic selection of optimal processing mode based on complexity',
      features: ['85% fast traditional', '15% multi-agent AI', '70% cost savings']
    },
    {
      icon: '🤖',
      title: 'OpenAI Integration',
      description: 'Hybrid Azure OpenAI and standard OpenAI with automatic fallback',
      features: ['GPT-4 Turbo', 'GPT-3.5 Turbo', 'Custom embeddings']
    },
    {
      icon: '📊',
      title: 'Advanced Analytics',
      description: 'Real-time metrics, automation tracking, and business intelligence',
      features: ['Automation rate', 'Cost analytics', 'Performance metrics']
    },
    {
      icon: '🔄',
      title: 'Workflow Automation',
      description: 'Configurable workflows with triggers, actions, and conditions',
      features: ['Event-driven', 'Custom rules', 'Integration ready']
    },
    {
      icon: '🏢',
      title: 'M365 Integration',
      description: 'Microsoft 365 Copilot-like capabilities for document intelligence',
      features: ['SharePoint sync', 'OneDrive integration', 'Teams collaboration']
    },
    {
      icon: '🛠️',
      title: 'MCP Protocol',
      description: 'Model Context Protocol for external AI agent integration',
      features: ['Claude integration', 'Tool execution', 'Resource access']
    }
  ];

  const techStack = {
    'AI & ML': ['Azure OpenAI', 'OpenAI GPT-4', 'LangChain', 'Form Recognizer', 'Custom ML Models'],
    'Backend': ['FastAPI', 'Python 3.11', 'Microservices', 'Event-Driven Architecture'],
    'Data': ['PostgreSQL', 'Redis', 'Azure Blob Storage', 'Vector Search'],
    'Frontend': ['React', 'TypeScript', 'Vite', 'Tailwind CSS'],
    'DevOps': ['Docker', 'Kubernetes', 'Prometheus', 'Grafana', 'Nginx']
  };

  return (
    <div className="space-y-8">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-8 text-white">
        <h1 className="text-4xl font-bold mb-4">Document Intelligence Platform</h1>
        <p className="text-xl text-blue-100 mb-2">
          Enterprise-grade AI-powered document processing with 90%+ automation
        </p>
        <p className="text-blue-200">
          Combining fine-tuned models, intelligent routing, LangChain orchestration, and advanced analytics
        </p>
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-6">AI Capabilities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {capabilities.map((cap, idx) => (
            <Card key={idx} className="hover:shadow-lg transition-shadow">
              <div className="text-center">
                <div className="text-5xl mb-4">{cap.icon}</div>
                <h3 className="font-bold text-lg mb-2">{cap.title}</h3>
                <p className="text-sm text-gray-600 mb-4">{cap.description}</p>
                <div className="space-y-1">
                  {cap.features.map((feature, i) => (
                    <div key={i} className="text-xs text-gray-500 flex items-center justify-center gap-1">
                      <span className="text-green-500">✓</span>
                      {feature}
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-6">Technology Stack</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          {Object.entries(techStack).map(([category, technologies]) => (
            <Card key={category} title={category}>
              <div className="space-y-2">
                {technologies.map((tech, idx) => (
                  <div key={idx} className="text-sm py-1 px-2 bg-gray-50 rounded">
                    {tech}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      </div>

      <Card title="Performance Metrics">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-600">90%+</div>
            <div className="text-sm text-gray-600">Automation Rate</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600">1.1s</div>
            <div className="text-sm text-gray-600">Avg Processing Time</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-600">$0.015</div>
            <div className="text-sm text-gray-600">Cost per Document</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-orange-600">70%</div>
            <div className="text-sm text-gray-600">Cost Savings</div>
          </div>
        </div>
      </Card>

      <Card title="Intelligent Routing">
        <div className="space-y-4">
          <p className="text-gray-700">
            Our intelligent routing system automatically analyzes document complexity and selects the optimal processing mode:
          </p>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="font-bold text-green-700 mb-2">Simple (85%)</div>
              <div className="text-sm text-gray-600">Traditional API</div>
              <div className="text-xs text-gray-500 mt-2">{'<'}1s, $0.01/doc</div>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <div className="font-bold text-yellow-700 mb-2">Medium (10%)</div>
              <div className="text-sm text-gray-600">Traditional + Fallback</div>
              <div className="text-xs text-gray-500 mt-2">1-2s, $0.02/doc</div>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="font-bold text-blue-700 mb-2">Complex (5%)</div>
              <div className="text-sm text-gray-600">Multi-Agent AI</div>
              <div className="text-xs text-gray-500 mt-2">3-5s, $0.05/doc</div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

