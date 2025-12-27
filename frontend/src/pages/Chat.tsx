import { useState, useRef, useEffect } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<string[]>(['Session 1']);
  const [activeSession, setActiveSession] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { 
      role: 'user', 
      content: input,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.post('/chat/message', { message: input });
      const assistantMsg: Message = { 
        role: 'assistant', 
        content: res.data.content || res.data.response || 'I apologize, but I could not process your request.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      const errorMsg: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const newSession = () => {
    setSessions([...sessions, `Session ${sessions.length + 1}`]);
    setActiveSession(sessions.length);
    setMessages([]);
  };

  const suggestedQuestions = [
    'What documents were processed today?',
    'Show me invoices from last month',
    'Extract key information from my latest document',
    'What is the automation rate?',
  ];

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6">
      {/* Sidebar */}
      <div className="w-64 space-y-4">
        <Button onClick={newSession} className="w-full">
          + New Chat
        </Button>
        
        <Card title="Chat Sessions">
          <div className="space-y-2">
            {sessions.map((session, idx) => (
              <button
                key={idx}
                onClick={() => setActiveSession(idx)}
                className={`w-full text-left px-3 py-2 rounded ${
                  activeSession === idx ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100'
                }`}
              >
                {session}
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <Card className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto mb-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <h2 className="text-2xl font-bold mb-4">AI Document Assistant</h2>
                <p className="text-gray-600 mb-6">Ask me anything about your documents</p>
                
                <div className="grid grid-cols-2 gap-3 max-w-2xl mx-auto">
                  {suggestedQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInput(q)}
                      className="p-3 text-left bg-gray-50 hover:bg-gray-100 rounded-lg text-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl px-4 py-3 rounded-lg ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-100 dark:bg-gray-700'
                  }`}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <p className={`text-xs mt-2 ${
                      msg.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                    }`}>
                      {msg.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))
            )}
            
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 px-4 py-3 rounded-lg">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          <div className="flex gap-2 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Type your message... (Shift+Enter for new line)"
              className="flex-1 px-4 py-3 border rounded-lg resize-none"
              rows={3}
            />
            <Button onClick={sendMessage} disabled={loading || !input.trim()}>
              Send
            </Button>
          </div>
        </Card>
      </div>

      {/* Right Sidebar */}
      <div className="w-64">
        <Card title="Context">
          <div className="space-y-2 text-sm">
            <p className="text-gray-600">Connected Documents: 0</p>
            <p className="text-gray-600">Active Workflows: 0</p>
            <Button variant="secondary" className="w-full mt-4">
              Add Context
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

