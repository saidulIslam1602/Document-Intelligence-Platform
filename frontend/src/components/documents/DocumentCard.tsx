import Badge from '../common/Badge';

interface DocumentCardProps {
  document: {
    id: string;
    filename: string;
    status: string;
    uploadedAt: string;
    fileSize?: number;
    extractedEntities?: number;
  };
  onClick?: () => void;
}

export default function DocumentCard({ document, onClick }: DocumentCardProps) {
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const getStatusVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'success';
      case 'processing': return 'warning';
      case 'failed': return 'error';
      default: return 'info';
    }
  };

  return (
    <div 
      onClick={onClick}
      className="card hover:shadow-lg transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-lg mb-2">{document.filename}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>{formatFileSize(document.fileSize)}</span>
            <span>•</span>
            <span>{new Date(document.uploadedAt).toLocaleDateString()}</span>
          </div>
          {document.extractedEntities !== undefined && (
            <p className="text-sm text-gray-600 mt-2">
              {document.extractedEntities} entities extracted
            </p>
          )}
        </div>
        <Badge variant={getStatusVariant(document.status)}>
          {document.status}
        </Badge>
      </div>
    </div>
  );
}

