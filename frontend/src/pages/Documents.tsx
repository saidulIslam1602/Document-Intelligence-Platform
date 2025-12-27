import { useState, useEffect } from 'react';
import api from '../services/api';
import { Document } from '../types';
import DocumentUpload from '../components/documents/DocumentUpload';
import DocumentCard from '../components/documents/DocumentCard';
import SearchBar from '../components/common/SearchBar';
import Modal from '../components/common/Modal';
import DocumentViewer from '../components/documents/DocumentViewer';
import Button from '../components/common/Button';

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [filteredDocs, setFilteredDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    const filtered = documents.filter(doc =>
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );
    setFilteredDocs(filtered);
  }, [searchQuery, documents]);

  const loadDocuments = async () => {
    try {
      const res = await api.get('/documents');
      setDocuments(res.data.documents || []);
    } catch (error) {
      console.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (files: FileList) => {
    setUploading(true);
    
    for (let i = 0; i < files.length; i++) {
      const formData = new FormData();
      formData.append('file', files[i]);

      try {
        await api.post('/documents/upload', formData);
      } catch (error) {
        console.error(`Failed to upload ${files[i].name}`);
      }
    }
    
    setUploading(false);
    setShowUpload(false);
    loadDocuments();
  };

  const viewDocument = async (docId: string) => {
    try {
      const res = await api.get(`/documents/${docId}`);
      setSelectedDoc(res.data);
    } catch (error) {
      console.error('Failed to load document');
    }
  };

  const deleteDocument = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await api.delete(`/documents/${docId}`);
      loadDocuments();
    } catch (error) {
      console.error('Failed to delete document');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Documents</h1>
        <div className="flex gap-2">
          <Button 
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            variant="secondary"
          >
            {viewMode === 'grid' ? '☰ List' : '⊞ Grid'}
          </Button>
          <Button onClick={() => setShowUpload(true)}>
            Upload Documents
          </Button>
        </div>
      </div>

      <SearchBar 
        value={searchQuery}
        onChange={setSearchQuery}
        placeholder="Search documents..."
      />

      {loading ? (
        <div className="flex items-center justify-center h-64">Loading...</div>
      ) : (
        <>
          {viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredDocs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onClick={() => viewDocument(doc.id)}
                />
              ))}
            </div>
          ) : (
            <div className="card">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3">Filename</th>
                    <th className="text-left py-3">Status</th>
                    <th className="text-left py-3">Date</th>
                    <th className="text-left py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocs.map((doc) => (
                    <tr key={doc.id} className="border-b hover:bg-gray-50">
                      <td className="py-3">{doc.filename}</td>
                      <td className="py-3">{doc.status}</td>
                      <td className="py-3">{new Date(doc.uploadedAt).toLocaleDateString()}</td>
                      <td className="py-3">
                        <button 
                          onClick={() => viewDocument(doc.id)}
                          className="text-blue-600 hover:underline mr-3"
                        >
                          View
                        </button>
                        <button 
                          onClick={() => deleteDocument(doc.id)}
                          className="text-red-600 hover:underline"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {filteredDocs.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <p>No documents found</p>
              <Button onClick={() => setShowUpload(true)} variant="primary" className="mt-4">
                Upload Your First Document
              </Button>
            </div>
          )}
        </>
      )}

      <Modal isOpen={showUpload} onClose={() => setShowUpload(false)} title="Upload Documents">
        <DocumentUpload onUpload={handleUpload} />
        {uploading && <p className="mt-4 text-center">Uploading...</p>}
      </Modal>

      <Modal 
        isOpen={!!selectedDoc} 
        onClose={() => setSelectedDoc(null)} 
        title={selectedDoc?.filename || 'Document'}
      >
        {selectedDoc && <DocumentViewer document={selectedDoc} />}
      </Modal>
    </div>
  );
}

