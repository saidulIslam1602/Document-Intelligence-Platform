import api from './api';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
}

export interface ChatSession {
  id: string;
  title: string;
  created: Date;
  updated: Date;
  messageCount: number;
}

class ChatService {
  async sendMessage(message: string, sessionId?: string): Promise<ChatMessage> {
    const response = await api.post('/chat/message', { 
      message, 
      session_id: sessionId 
    });
    
    return {
      role: 'assistant',
      content: response.data.content || response.data.response,
      timestamp: new Date()
    };
  }

  async getSessions(): Promise<ChatSession[]> {
    const response = await api.get('/chat/sessions');
    return response.data.sessions || [];
  }

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const response = await api.get(`/chat/sessions/${sessionId}/messages`);
    return response.data.messages || [];
  }

  async createSession(title: string): Promise<ChatSession> {
    const response = await api.post('/chat/sessions', { title });
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await api.delete(`/chat/sessions/${sessionId}`);
  }

  async streamMessage(message: string, onChunk: (chunk: string) => void): Promise<void> {
    const response = await fetch(`${api.defaults.baseURL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ message })
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        onChunk(chunk);
      }
    }
  }
}

export default new ChatService();

