interface FileIconProps {
  filename: string;
  size?: 'small' | 'medium' | 'large';
}

export default function FileIcon({ filename, size = 'medium' }: FileIconProps) {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  
  const sizes = {
    small: 'text-2xl',
    medium: 'text-4xl',
    large: 'text-6xl'
  };

  const getIcon = () => {
    switch (ext) {
      case 'pdf': return '📕';
      case 'doc':
      case 'docx': return '📘';
      case 'xls':
      case 'xlsx': return '📊';
      case 'ppt':
      case 'pptx': return '📙';
      case 'txt': return '📄';
      case 'csv': return '📋';
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'bmp':
      case 'webp': return '🖼️';
      case 'zip':
      case 'rar':
      case '7z': return '📦';
      case 'mp4':
      case 'avi':
      case 'mov': return '🎬';
      case 'mp3':
      case 'wav': return '🎵';
      default: return '📎';
    }
  };

  return (
    <span className={sizes[size]}>
      {getIcon()}
    </span>
  );
}

