# Azure imports (optional)
try:
    from azure.storage.filedatalake import DataLakeServiceClient
    from azure.core.exceptions import ResourceNotFoundError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    DataLakeServiceClient = None
    ResourceNotFoundError = Exception

import logging
from typing import Optional, List
import json

class DataLakeService:
    """Service for Azure Data Lake Storage Gen2 operations"""
    
    def __init__(self, connection_string: str):
        self.logger = logging.getLogger(__name__)
        self.service_client = None
        self.enabled = False
        
        if connection_string and connection_string.strip():
            try:
                self.service_client = DataLakeServiceClient.from_connection_string(connection_string)
                self.enabled = True
                self.logger.info("Data Lake Service initialized successfully")
            except Exception as e:
                self.logger.warning(f"Data Lake Service not available: {str(e)}")
        else:
            self.logger.info("Data Lake Service disabled (no connection string provided)")
    
    def upload_file(self, file_system: str, file_path: str, data: bytes, 
                   metadata: Optional[dict] = None) -> bool:
        """Upload a file to Data Lake"""
        if not self.enabled:
            self.logger.debug("Data Lake Service not enabled, skipping upload")
            return False
        
        try:
            file_client = self.service_client.get_file_client(
                file_system=file_system, 
                file_path=file_path
            )
            
            file_client.create_file()
            file_client.append_data(data, offset=0, length=len(data))
            file_client.flush_data(len(data))
            
            if metadata:
                file_client.set_metadata(metadata)
            
            self.logger.info(f"Successfully uploaded file to {file_system}/{file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload file: {str(e)}")
            return False
    
    def download_file(self, file_system: str, file_path: str) -> Optional[bytes]:
        """Download a file from Data Lake"""
        if not self.enabled:
            self.logger.debug("Data Lake Service not enabled, skipping download")
            return None
        
        try:
            file_client = self.service_client.get_file_client(
                file_system=file_system, 
                file_path=file_path
            )
            
            download = file_client.download_file()
            return download.readall()
            
        except ResourceNotFoundError:
            self.logger.warning(f"File not found: {file_system}/{file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to download file: {str(e)}")
            return None
    
    def list_files(self, file_system: str, path: str = "") -> List[str]:
        """List files in a Data Lake directory"""
        try:
            paths = self.service_client.get_paths(
                file_system=file_system, 
                path=path
            )
            return [path.name for path in paths if not path.is_directory]
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {str(e)}")
            return []
    
    def create_directory(self, file_system: str, directory_path: str) -> bool:
        """Create a directory in Data Lake"""
        try:
            directory_client = self.service_client.get_directory_client(
                file_system=file_system, 
                directory_path=directory_path
            )
            directory_client.create_directory()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create directory: {str(e)}")
            return False
    
    def store_analytics_data(self, data: dict, file_name: str) -> bool:
        """Store analytics data in the analytics-data container"""
        try:
            json_data = json.dumps(data, indent=2).encode('utf-8')
            return self.upload_file(
                file_system="analytics-data",
                file_path=f"analytics/{file_name}",
                data=json_data,
                metadata={"content_type": "application/json"}
            )
        except Exception as e:
            self.logger.error(f"Failed to store analytics data: {str(e)}")
            return False
    
    def store_raw_data(self, data: bytes, file_name: str, content_type: str = "application/octet-stream") -> bool:
        """Store raw data in the raw-data container"""
        try:
            return self.upload_file(
                file_system="raw-data",
                file_path=f"ingestion/{file_name}",
                data=data,
                metadata={"content_type": content_type}
            )
        except Exception as e:
            self.logger.error(f"Failed to store raw data: {str(e)}")
            return False
    
    def store_processed_data(self, data: dict, file_name: str) -> bool:
        """Store processed data in the processed-data container"""
        try:
            json_data = json.dumps(data, indent=2).encode('utf-8')
            return self.upload_file(
                file_system="processed-data",
                file_path=f"processed/{file_name}",
                data=json_data,
                metadata={"content_type": "application/json"}
            )
        except Exception as e:
            self.logger.error(f"Failed to store processed data: {str(e)}")
            return False