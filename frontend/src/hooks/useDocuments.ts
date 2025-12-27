import { useState, useEffect } from 'react';
import api from '../services/api';
import { Document } from '../types';

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const res = await api.get('/documents');
      setDocuments(res.data.documents || []);
      setError(null);
    } catch (err) {
      setError('Failed to load documents');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const uploadDocument = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await api.post('/documents/upload', formData);
      await loadDocuments();
      return { success: true };
    } catch (err) {
      return { success: false, error: 'Upload failed' };
    }
  };

  const deleteDocument = async (id: string) => {
    try {
      await api.delete(`/documents/${id}`);
      await loadDocuments();
      return { success: true };
    } catch (err) {
      return { success: false, error: 'Delete failed' };
    }
  };

  return {
    documents,
    loading,
    error,
    loadDocuments,
    uploadDocument,
    deleteDocument
  };
}

