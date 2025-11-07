"""
Azure Blob Storage service for file management.
"""

import os
import uuid
import logging
from typing import Optional, BinaryIO
from io import BytesIO
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
from azure.core.exceptions import AzureError, ResourceNotFoundError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class AzureBlobStorageService:
    """Service for managing files in Azure Blob Storage."""

    def __init__(
        self,
        account_name: str = None,
        account_key: str = None,
        connection_string: str = None,
        container_name: str = "crm-files"
    ):
        """
        Initialize Azure Blob Storage service.

        Args:
            account_name: Azure storage account name
            account_key: Azure storage account key
            connection_string: Azure storage connection string (alternative to account_name/key)
            container_name: Name of the blob container
        """
        self.container_name = container_name

        try:
            if connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
            elif account_name and account_key:
                self.blob_service_client = BlobServiceClient(
                    account_url=f"https://{account_name}.blob.core.windows.net",
                    credential=account_key
                )
            else:
                raise ValueError(
                    "Either connection_string or account_name/account_key must be provided")

            # Ensure container exists
            self._ensure_container_exists()

        except Exception as e:
            logger.error(
                f"Failed to initialize Azure Blob Storage service: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize cloud storage service"
            )

    def _ensure_container_exists(self):
        """Ensure the blob container exists, create if it doesn't."""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            # Try to get container properties, create if it doesn't exist
            try:
                container_client.get_container_properties()
            except ResourceNotFoundError:
                container_client.create_container(public_access=None)
                logger.info(f"Created blob container: {self.container_name}")

        except AzureError as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to access cloud storage container"
            )

    def upload_file(
        self,
        file_content: bytes,
        blob_name: str,
        content_type: str = None,
        folder: str = "documents"
    ) -> str:
        """
        Upload a file to Azure Blob Storage.

        Args:
            file_content: File content as bytes
            blob_name: Name for the blob
            content_type: MIME type of the file
            folder: Folder/prefix for organizing files

        Returns:
            The blob URL/path
        """
        try:
            # Create full blob path with folder
            full_blob_name = f"{folder}/{blob_name}" if folder else blob_name

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=full_blob_name
            )

            # Upload with metadata
            metadata = {
                "uploaded_at": str(uuid.uuid4()),
                "content_type": content_type or "application/octet-stream"
            }

            blob_client.upload_blob(
                file_content,
                content_settings=ContentSettings(
                    content_type=content_type or "application/octet-stream"
                ),
                metadata=metadata,
                overwrite=True
            )

            logger.info(
                f"Successfully uploaded file to Azure Blob Storage: {full_blob_name}")
            return full_blob_name

        except AzureError as e:
            logger.error(f"Failed to upload file to Azure Blob Storage: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to cloud storage"
            )

    def download_file(self, blob_name: str) -> bytes:
        """
        Download a file from Azure Blob Storage.

        Args:
            blob_name: Name/path of the blob to download

        Returns:
            File content as bytes
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            download_stream = blob_client.download_blob()
            return download_stream.readall()

        except ResourceNotFoundError:
            logger.error(f"File not found in Azure Blob Storage: {blob_name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        except AzureError as e:
            logger.error(
                f"Failed to download file from Azure Blob Storage: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download file from cloud storage"
            )

    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from Azure Blob Storage.

        Args:
            blob_name: Name/path of the blob to delete

        Returns:
            True if deleted successfully
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            blob_client.delete_blob()
            logger.info(
                f"Successfully deleted file from Azure Blob Storage: {blob_name}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"File not found for deletion: {blob_name}")
            return False
        except AzureError as e:
            logger.error(f"Failed to delete file from Azure Blob Storage: {e}")
            return False

    def get_file_url(self, blob_name: str) -> str:
        """
        Get the URL for a blob.

        Args:
            blob_name: Name/path of the blob

        Returns:
            The blob URL
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        return blob_client.url

    def file_exists(self, blob_name: str) -> bool:
        """
        Check if a file exists in Azure Blob Storage.

        Args:
            blob_name: Name/path of the blob to check

        Returns:
            True if file exists
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except AzureError:
            return False

    def get_file_info(self, blob_name: str) -> dict:
        """
        Get file information from Azure Blob Storage.

        Args:
            blob_name: Name/path of the blob

        Returns:
            Dictionary with file information
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            properties = blob_client.get_blob_properties()

            return {
                "name": blob_name,
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "last_modified": properties.last_modified,
                "etag": properties.etag,
                "metadata": properties.metadata,
                "url": blob_client.url
            }

        except ResourceNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        except AzureError as e:
            logger.error(
                f"Failed to get file info from Azure Blob Storage: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get file information"
            )
