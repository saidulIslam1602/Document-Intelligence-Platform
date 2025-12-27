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
      doc.filename?.toLowerCase().includes(searchQuery.toLowerCase())
    );
    setFilteredDocs(filtered);
  }, [searchQuery, documents]);

  const loadDocuments = async () => {
    try {
      const res = await api.get('/documents');
      // Transform snake_case to camelCase for frontend components
      const transformedDocs = (res.data.documents || []).map((doc: any) => ({
        ...doc,
        uploadedAt: doc.uploaded_at,
        fileSize: doc.file_size,
        extractedEntities: 0 // Can be updated later if we add entity count to API
      }));
      setDocuments(transformedDocs);
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
    
    console.log('Starting upload for', selectedFiles.length, 'file(s)');
    setUploading(true);
    
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      console.log('Uploading file:', file.name, 'Size:', file.size, 'Type:', file.type);
      
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
        console.error('Upload error for', file.name, ':', error);
        console.error('Error response:', error.response?.data);
        console.error('Error status:', error.response?.status);
        
        // Get detailed error message
        let errorMessage = 'Upload failed';
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        // Mark as error
        setUploadProgress(prev => prev.map((item, idx) => 
          idx === i ? { 
            ...item, 
            status: 'error', 
            progress: 0,
            error: errorMessage
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
      const docData = res.data;
      
      // Transform invoice extraction data for display
      let content = '';
      if (docData.invoice_number) {
        content = `INVOICE EXTRACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Invoice Details:
   Invoice Number:    ${docData.invoice_number || 'N/A'}
   Invoice Date:      ${docData.invoice_date || 'N/A'}
   Due Date:          ${docData.due_date || 'N/A'}
   PO Number:         ${docData.purchase_order_number || 'N/A'}

👤 Vendor Information:
   Name:              ${docData.vendor_name || 'N/A'}
   Address:           ${docData.vendor_address || 'N/A'}
   Tax ID:            ${docData.vendor_tax_id || 'N/A'}
   Email:             ${docData.vendor_email || 'N/A'}
   Phone:             ${docData.vendor_phone || 'N/A'}

🏢 Customer Information:
   Name:              ${docData.customer_name || 'N/A'}
   Address:           ${docData.customer_address || 'N/A'}
   Tax ID:            ${docData.customer_tax_id || 'N/A'}

💰 Financial Summary:
   Subtotal:          ${docData.currency_code || 'USD'} ${docData.subtotal || '0.00'}
   Tax (${docData.tax_rate || '0'}%):         ${docData.currency_code || 'USD'} ${docData.tax_amount || '0.00'}
   Discount:          ${docData.currency_code || 'USD'} ${docData.discount_amount || '0.00'}
   Shipping:          ${docData.currency_code || 'USD'} ${docData.shipping_amount || '0.00'}
   ═══════════════════════════════════════════════
   TOTAL:             ${docData.currency_code || 'USD'} ${docData.total_amount || '0.00'}
   Amount Paid:       ${docData.currency_code || 'USD'} ${docData.amount_paid || '0.00'}
   Balance Due:       ${docData.currency_code || 'USD'} ${docData.balance_due || '0.00'}

📋 Line Items:`;
        
        if (docData.line_items && Array.isArray(docData.line_items)) {
          docData.line_items.forEach((item: any, idx: number) => {
            content += `
   ${idx + 1}. ${item.description || 'N/A'}
      Quantity: ${item.quantity || 0} × ${docData.currency_code || 'USD'} ${item.unit_price || '0.00'} = ${docData.currency_code || 'USD'} ${item.amount || '0.00'}`;
          });
        }
        
        content += `

💳 Payment Terms:
   Payment Terms:     ${docData.payment_terms || 'N/A'}
   Payment Method:    ${docData.payment_method || 'N/A'}

🏦 Banking Details:
   Bank Name:         ${docData.bank_name || 'N/A'}
   Account Number:    ${docData.bank_account_number || 'N/A'}
   Routing Number:    ${docData.bank_routing_number || 'N/A'}

📝 Notes:
   ${docData.notes || 'N/A'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extraction Confidence: ${((docData.confidence_score || 0) * 100).toFixed(1)}%`;
      }
      
      // Transform to DocumentViewer format
      const transformedDoc = {
        id: docData.id,
        filename: docData.filename,
        content: content || 'No extraction data available',
        entities: docData.entities || [],
        metadata: {
          file_type: docData.file_type,
          document_type: docData.document_type,
          status: docData.status,
          file_size: docData.file_size,
          uploaded_at: docData.uploaded_at,
          confidence_score: docData.confidence_score,
          // Include all invoice fields for metadata view
          ...docData
        }
      };
      
      setSelectedDoc(transformedDoc);
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
        <div>
          <h1 className="text-3xl font-bold">Documents</h1>
          <p className="text-sm text-gray-500 mt-1">Upload and manage your documents</p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            variant="secondary"
          >
            {viewMode === 'grid' ? '☰ List' : '⊞ Grid'}
          </Button>
          <Button onClick={() => setShowUpload(true)}>
            📤 Upload
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

          {filteredDocs.length === 0 && !loading && (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">📄</div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">No documents yet</h3>
              <p className="text-gray-500 mb-6">Get started by uploading your first document</p>
              <Button onClick={() => setShowUpload(true)} variant="primary">
                📤 Upload Document
              </Button>
            </div>
          )}
        </>
      )}

      <Modal isOpen={showUpload} onClose={cancelUpload} title={selectedFiles.length > 0 ? `Uploading ${selectedFiles.length} file(s)` : 'Upload Documents'}>
        {selectedFiles.length === 0 ? (
          <div>
            <DocumentUpload onUpload={handleFilesSelected} />
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600">
                💡 <strong>Tip:</strong> You can select multiple files at once for batch upload (up to 100 files)
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {uploadProgress.map((progress, idx) => (
                <div key={idx} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-lg">
                        {progress.status === 'success' && '✅'}
                        {progress.status === 'error' && '❌'}
                        {progress.status === 'uploading' && '⏳'}
                        {progress.status === 'pending' && '📄'}
                      </span>
                      <span className="text-sm font-medium truncate">
                        {progress.file}
                      </span>
                    </div>
                    <span className={`text-xs font-medium px-2 py-1 rounded ${
                      progress.status === 'success' ? 'bg-green-100 text-green-700' :
                      progress.status === 'error' ? 'bg-red-100 text-red-700' :
                      progress.status === 'uploading' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {progress.status === 'success' && 'Done'}
                      {progress.status === 'error' && 'Failed'}
                      {progress.status === 'uploading' && `${progress.progress}%`}
                      {progress.status === 'pending' && 'Waiting'}
                    </span>
                  </div>
                  
                  {(progress.status === 'uploading' || progress.status === 'success') && (
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          progress.status === 'success' ? 'bg-green-600' : 'bg-blue-600'
                        }`}
                        style={{ width: `${progress.progress}%` }}
                      ></div>
                    </div>
                  )}
                  
                  {progress.status === 'error' && progress.error && (
                    <p className="text-xs text-red-600 mt-1 ml-7">{progress.error}</p>
                  )}
                </div>
              ))}
            </div>
            
            <div className="flex gap-2 pt-3 border-t">
              <Button
                onClick={startUpload}
                disabled={uploading}
                className="flex-1"
              >
                {uploading ? '⏳ Uploading...' : '📤 Upload All'}
              </Button>
              {!uploading && (
                <>
                  <Button
                    onClick={() => {
                      setSelectedFiles([]);
                      setUploadProgress([]);
                    }}
                    variant="secondary"
                  >
                    Clear
                  </Button>
                  <Button
                    onClick={cancelUpload}
                    variant="secondary"
                  >
                    Cancel
                  </Button>
                </>
              )}
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

