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
  onDelete?: (id: string, event: React.MouseEvent) => void;
}

export default function DocumentCard({ document, onClick, onDelete }: DocumentCardProps) {
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
      className="card hover:shadow-lg transition-shadow cursor-pointer relative group"
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
        <div className="flex flex-col items-end gap-2">
          <Badge variant={getStatusVariant(document.status)}>
            {document.status}
          </Badge>
          {onDelete && (
            <button
              onClick={(e) => onDelete(document.id, e)}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-800 text-sm font-medium"
              title="Delete document"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

