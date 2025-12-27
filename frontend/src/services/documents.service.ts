import api from './api';
import { Document } from '../types';

class DocumentsService {
  async getAll(params?: { limit?: number; offset?: number; status?: string }): Promise<Document[]> {
    const response = await api.get('/documents', { params });
    return response.data.documents || [];
  }

  async getById(id: string): Promise<Document> {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  }

  async upload(file: File, onProgress?: (progress: number) => void): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      }
    });

    return response.data;
  }

  async batchUpload(files: File[]): Promise<Document[]> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response = await api.post('/documents/batch-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    return response.data.documents || [];
  }

  async delete(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
  }

  async download(id: string): Promise<Blob> {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob'
    });
    return response.data;
  }

  async reprocess(id: string): Promise<Document> {
    const response = await api.post(`/documents/${id}/reprocess`);
    return response.data;
  }

  async getContent(id: string): Promise<string> {
    const response = await api.get(`/documents/${id}/content`);
    return response.data.content;
  }

  async getEntities(id: string) {
    const response = await api.get(`/documents/${id}/entities`);
    return response.data.entities || [];
  }

  async search(query: string, filters?: any) {
    const response = await api.post('/documents/search', { query, ...filters });
    return response.data.results || [];
  }
}

export default new DocumentsService();

