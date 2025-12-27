import { useState } from 'react';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import ProgressBar from '../components/common/ProgressBar';
import documentsService from '../services/documents.service';

interface UploadFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  error?: string;
}

export default function BatchUpload() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles: UploadFile[] = selectedFiles.map(file => ({
      id: Math.random().toString(36),
      file,
      status: 'pending',
      progress: 0
    }));
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const uploadBatch = async () => {
    setUploading(true);

    for (const fileItem of files) {
      if (fileItem.status !== 'pending') continue;

      setFiles(prev => prev.map(f => 
        f.id === fileItem.id ? {...f, status: 'uploading'} : f
      ));

      try {
        await documentsService.upload(fileItem.file, (progress) => {
          setFiles(prev => prev.map(f =>
            f.id === fileItem.id ? {...f, progress} : f
          ));
        });

        setFiles(prev => prev.map(f =>
          f.id === fileItem.id ? {...f, status: 'completed', progress: 100} : f
        ));
      } catch (error) {
        setFiles(prev => prev.map(f =>
          f.id === fileItem.id ? {...f, status: 'failed', error: 'Upload failed'} : f
        ));
      }
    }

    setUploading(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'uploading': return 'text-blue-600';
      default: return 'text-gray-600';
    }
  };

  const stats = {
    total: files.length,
    pending: files.filter(f => f.status === 'pending').length,
    uploading: files.filter(f => f.status === 'uploading').length,
    completed: files.filter(f => f.status === 'completed').length,
    failed: files.filter(f => f.status === 'failed').length
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Batch Upload</h1>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <p className="text-sm text-gray-500">Total</p>
          <p className="text-2xl font-bold">{stats.total}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Pending</p>
          <p className="text-2xl font-bold text-gray-600">{stats.pending}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Uploading</p>
          <p className="text-2xl font-bold text-blue-600">{stats.uploading}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Completed</p>
          <p className="text-2xl font-bold text-green-600">{stats.completed}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
        </Card>
      </div>

      <Card>
        <div className="space-y-4">
          <div className="flex gap-3">
            <label className="btn btn-primary cursor-pointer">
              Select Files
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.tiff,.tif"
                disabled={uploading}
              />
            </label>
            <Button
              onClick={uploadBatch}
              disabled={files.length === 0 || uploading || stats.pending === 0}
            >
              Upload All ({stats.pending})
            </Button>
            <Button
              variant="secondary"
              onClick={() => setFiles([])}
              disabled={uploading}
            >
              Clear All
            </Button>
          </div>

          <p className="text-sm text-gray-500">
            Select up to 100 files (max 20MB each). Supported: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, TIFF
          </p>
        </div>
      </Card>

      {files.length > 0 && (
        <Card title={`Files (${files.length})`}>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {files.map(fileItem => (
              <div key={fileItem.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <p className="font-medium">{fileItem.file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(fileItem.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  {fileItem.status === 'uploading' && (
                    <div className="mt-2">
                      <ProgressBar progress={fileItem.progress} size="small" />
                    </div>
                  )}
                  {fileItem.error && (
                    <p className="text-sm text-red-600 mt-1">{fileItem.error}</p>
                  )}
                </div>

                <div className={`font-medium capitalize ${getStatusColor(fileItem.status)}`}>
                  {fileItem.status}
                </div>

                {fileItem.status === 'pending' && (
                  <button
                    onClick={() => removeFile(fileItem.id)}
                    className="text-red-600 hover:text-red-800"
                    disabled={uploading}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

