import { useState, useEffect } from 'react';
import api from '../services/api';
import documentsService from '../services/documents.service';
import { Document } from '../types';
import DocumentUpload from '../components/documents/DocumentUpload';
import DocumentCard from '../components/documents/DocumentCard';
import SearchBar from '../components/common/SearchBar';
import Modal from '../components/common/Modal';
import DocumentViewer from '../components/documents/DocumentViewer';
import Button from '../components/common/Button';

interface UploadProgress {
  file: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [filteredDocs, setFilteredDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

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

  const handleFilesSelected = (files: FileList) => {
    const fileArray = Array.from(files);
    setSelectedFiles(fileArray);
    
    // Initialize upload progress
    const progress: UploadProgress[] = fileArray.map(file => ({
      file: file.name,
      status: 'pending',
      progress: 0,
    }));
    setUploadProgress(progress);
  };

  const startUpload = async () => {
    if (selectedFiles.length === 0) return;
    
    setUploading(true);
    
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      
      // Update status to uploading
      setUploadProgress(prev => prev.map((item, idx) => 
        idx === i ? { ...item, status: 'uploading', progress: 0 } : item
      ));

      try {
        // Upload with real progress tracking
        await documentsService.upload(file, (progress) => {
          setUploadProgress(prev => prev.map((item, idx) => 
            idx === i ? { ...item, progress: Math.round(progress) } : item
          ));
        });
        
        // Mark as success
        setUploadProgress(prev => prev.map((item, idx) => 
          idx === i ? { ...item, status: 'success', progress: 100 } : item
        ));
      } catch (error: any) {
        // Mark as error
        setUploadProgress(prev => prev.map((item, idx) => 
          idx === i ? { 
            ...item, 
            status: 'error', 
            progress: 0,
            error: error.response?.data?.detail || 'Upload failed'
          } : item
        ));
      }
    }
    
    setUploading(false);
    
    // Wait a moment to show final status
    setTimeout(() => {
      // Check if we should auto-close
      const hasErrors = uploadProgress.some(item => item.status === 'error');
      if (!hasErrors) {
        setShowUpload(false);
        setSelectedFiles([]);
        setUploadProgress([]);
        loadDocuments();
      }
    }, 1500);
  };

  const cancelUpload = () => {
    setShowUpload(false);
    setSelectedFiles([]);
    setUploadProgress([]);
    setUploading(false);
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

      <Modal isOpen={showUpload} onClose={cancelUpload} title="Upload Documents">
        {selectedFiles.length === 0 ? (
          <DocumentUpload onUpload={handleFilesSelected} />
        ) : (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm font-medium text-blue-900">
                {selectedFiles.length} file(s) selected
              </p>
            </div>
            
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {uploadProgress.map((progress, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium truncate flex-1 mr-4">
                      {progress.file}
                    </span>
                    {progress.status === 'success' && (
                      <span className="text-green-600 font-medium">✓ Done</span>
                    )}
                    {progress.status === 'error' && (
                      <span className="text-red-600 font-medium">✗ Failed</span>
                    )}
                    {progress.status === 'uploading' && (
                      <span className="text-blue-600 font-medium">Uploading...</span>
                    )}
                    {progress.status === 'pending' && (
                      <span className="text-gray-500 font-medium">Pending</span>
                    )}
                  </div>
                  
                  {/* Progress bar */}
                  {(progress.status === 'uploading' || progress.status === 'success') && (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          progress.status === 'success' ? 'bg-green-600' : 'bg-blue-600'
                        }`}
                        style={{ width: `${progress.progress}%` }}
                      ></div>
                    </div>
                  )}
                  
                  {/* Error message */}
                  {progress.status === 'error' && progress.error && (
                    <p className="text-xs text-red-600 mt-1">{progress.error}</p>
                  )}
                </div>
              ))}
            </div>
            
            <div className="flex gap-3 pt-4 border-t">
              <Button
                onClick={startUpload}
                disabled={uploading}
                className="flex-1"
              >
                {uploading ? 'Uploading...' : 'Start Upload'}
              </Button>
              <Button
                onClick={() => {
                  setSelectedFiles([]);
                  setUploadProgress([]);
                }}
                variant="secondary"
                disabled={uploading}
              >
                Clear
              </Button>
              <Button
                onClick={cancelUpload}
                variant="secondary"
                disabled={uploading}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
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

