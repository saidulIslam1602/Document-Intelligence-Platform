"""
Local Storage Service for AI Processing
Provides file-based storage for local development without Azure dependencies
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class LocalStorageService:
    """Local file-based storage for development"""
    
    def __init__(self, base_path: str = "/tmp/document_storage"):
        self.base_path = Path(base_path)
        self.documents_path = self.base_path / "documents"
        self.metadata_path = self.base_path / "metadata"
        
        # Create directories
        self.documents_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Local storage initialized at {self.base_path}")
    
    def get_document_metadata(self, document_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get document metadata from local storage"""
        try:
            metadata_file = self.metadata_path / f"{document_id}.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            logger.warning(f"Document metadata not found: {document_id}")
            return None
        except Exception as e:
            logger.error(f"Error reading document metadata: {str(e)}")
            return None
    
    def save_document_metadata(self, document_id: str, metadata: Dict[str, Any]):
        """Save document metadata to local storage"""
        try:
            metadata_file = self.metadata_path / f"{document_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.info(f"Document metadata saved: {document_id}")
        except Exception as e:
            logger.error(f"Error saving document metadata: {str(e)}")
    
    def get_document_content(self, blob_path: str) -> Optional[bytes]:
        """Get document content from local storage"""
        try:
            # Extract document ID from blob_path
            # Format: documents/user_id/document_id/filename
            parts = blob_path.split('/')
            if len(parts) >= 3:
                document_id = parts[2]
                filename = parts[-1]
                
                # Try to find the file
                doc_file = self.documents_path / document_id / filename
                if doc_file.exists():
                    with open(doc_file, 'rb') as f:
                        return f.read()
            
            logger.warning(f"Document content not found: {blob_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading document content: {str(e)}")
            return None
    
    def save_document_content(self, document_id: str, filename: str, content: bytes):
        """Save document content to local storage"""
        try:
            doc_dir = self.documents_path / document_id
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            doc_file = doc_dir / filename
            with open(doc_file, 'wb') as f:
                f.write(content)
            logger.info(f"Document content saved: {document_id}/{filename}")
        except Exception as e:
            logger.error(f"Error saving document content: {str(e)}")

# Global instance
local_storage = LocalStorageService()
