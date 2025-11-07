"""
File storage factory for handling different storage backends.
"""

import os
import uuid
import logging
from typing import Protocol, Union
from fastapi import HTTPException, status
from .azure_blob_service import AzureBlobStorageService

logger = logging.getLogger(__name__)


class FileStorageProtocol(Protocol):
    """Protocol defining the interface for file storage services."""

    def upload_file(self, file_content: bytes, blob_name: str, content_type: str = None, folder: str = "documents") -> str:
        """Upload a file and return the storage path/URL."""
        ...

    def download_file(self, file_path: str) -> bytes:
        """Download a file and return its content."""
        ...

    def delete_file(self, file_path: str) -> bool:
        """Delete a file and return success status."""
        ...

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        ...

    def get_file_info(self, file_path: str) -> dict:
        """Get file information."""
        ...


class LocalFileStorage:
    """Local file storage implementation."""

    def __init__(self, base_path: str = "uploads"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def upload_file(self, file_content: bytes, blob_name: str, content_type: str = None, folder: str = "documents") -> str:
        """Upload a file to local storage."""
        try:
            # Create folder path
            folder_path = os.path.join(self.base_path, folder)
            os.makedirs(folder_path, exist_ok=True)

            # Generate unique filename (blob_name already includes the UUID-based name)
            file_path = os.path.join(folder_path, blob_name)

            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Return relative path for storage in database
            return os.path.join(folder, blob_name).replace("\\", "/")

        except Exception as e:
            logger.error(f"Failed to save file locally: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file"
            )

    def download_file(self, file_path: str) -> bytes:
        """Download a file from local storage."""
        try:
            full_path = os.path.join(self.base_path, file_path)

            if not os.path.exists(full_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            with open(full_path, "rb") as f:
                return f.read()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to read file locally: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to read file"
            )

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from local storage."""
        try:
            full_path = os.path.join(self.base_path, file_path)

            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete file locally: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in local storage."""
        full_path = os.path.join(self.base_path, file_path)
        return os.path.exists(full_path)

    def get_file_info(self, file_path: str) -> dict:
        """Get file information from local storage."""
        try:
            full_path = os.path.join(self.base_path, file_path)

            if not os.path.exists(full_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            stat = os.stat(full_path)

            return {
                "name": os.path.basename(file_path),
                "size": stat.st_size,
                "path": file_path,
                "last_modified": stat.st_mtime
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get file information"
            )


class FileStorageFactory:
    """Factory for creating file storage services based on configuration."""

    @staticmethod
    def get_storage_service(
        storage_backend: str = "local",
        **kwargs
    ) -> Union[LocalFileStorage, AzureBlobStorageService]:
        """
        Get the appropriate storage service based on configuration.

        Args:
            storage_backend: Type of storage backend ('local', 'azure_blob')
            **kwargs: Additional configuration for the storage service

        Returns:
            Storage service instance
        """
        if storage_backend == "azure_blob":
            # Get Azure configuration from environment or kwargs
            account_name = kwargs.get("account_name") or os.getenv(
                "AZURE_STORAGE_ACCOUNT_NAME")
            account_key = kwargs.get("account_key") or os.getenv(
                "AZURE_STORAGE_ACCOUNT_KEY")
            connection_string = kwargs.get("connection_string") or os.getenv(
                "AZURE_STORAGE_CONNECTION_STRING")
            container_name = kwargs.get("container_name") or os.getenv(
                "AZURE_BLOB_CONTAINER_NAME", "crm-files")

            if not (connection_string or (account_name and account_key)):
                logger.error("Azure Blob Storage configuration missing")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Cloud storage configuration missing"
                )

            return AzureBlobStorageService(
                account_name=account_name,
                account_key=account_key,
                connection_string=connection_string,
                container_name=container_name
            )

        elif storage_backend == "local":
            base_path = kwargs.get("base_path", "uploads")
            return LocalFileStorage(base_path=base_path)

        else:
            logger.error(f"Unknown storage backend: {storage_backend}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid storage configuration"
            )


# Dependency function for FastAPI
def get_file_storage_service() -> Union[LocalFileStorage, AzureBlobStorageService]:
    """Get the configured file storage service."""
    from ..core.config import settings

    # Use settings instead of direct os.getenv
    storage_backend = settings.STORAGE_BACKEND

    return FileStorageFactory.get_storage_service(
        storage_backend=storage_backend,
        account_name=getattr(settings, 'AZURE_STORAGE_ACCOUNT_NAME', None),
        account_key=getattr(settings, 'AZURE_STORAGE_ACCOUNT_KEY', None),
        connection_string=getattr(
            settings, 'AZURE_STORAGE_CONNECTION_STRING', None),
        container_name=getattr(settings, 'AZURE_BLOB_CONTAINER_NAME', None)
    )
