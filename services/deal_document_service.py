"""
Deal Document service for business logic.
"""

import os
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from models.deal_document import DealDocument
from models.deal import Deal
from models.user import UserProfile
from file_storage_factory import get_file_storage_service


class DealDocumentService:
    """Service class for deal document business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.storage_service = get_file_storage_service()

    def get_deal_documents(self, deal_id: uuid.UUID) -> List[DealDocument]:
        """
        Retrieve all documents for a specific deal.

        Args:
            deal_id: UUID of the deal

        Returns:
            List of DealDocument objects
        """
        return (
            self.db.query(DealDocument)
            .filter(DealDocument.deal_id == deal_id)
            .order_by(DealDocument.created_at.desc())
            .all()
        )

    async def upload_document(
        self,
        deal_id: uuid.UUID,
        file: UploadFile,
        current_user: UserProfile,
        folder: str = "deals"
    ) -> DealDocument:
        """
        Upload a document for a deal using the configured storage backend.

        Args:
            deal_id: UUID of the deal
            file: The uploaded file
            current_user: The user uploading the document
            folder: Folder/prefix for organizing files

        Returns:
            Created DealDocument object
        """
        # Verify deal exists
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deal not found"
            )

        try:
            # Read file content
            contents = await file.read()

            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # Upload file using storage service
            file_path = self.storage_service.upload_file(
                file_content=contents,
                blob_name=unique_filename,
                content_type=file.content_type,
                folder=folder
            )

            # Get file size
            file_size = len(contents)

            # Create database record
            document = DealDocument(
                name=file.filename,
                file_path=file_path,
                file_size=str(file_size),
                mime_type=file.content_type,
                deal_id=deal_id,
                uploaded_by=current_user.id
            )

            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)

            return document

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload document: {str(e)}"
            )

    def delete_document(self, document_id: uuid.UUID) -> bool:
        """
        Delete a document using the configured storage backend.

        Args:
            document_id: UUID of the document to delete

        Returns:
            True if deleted successfully
        """
        document = (
            self.db.query(DealDocument)
            .filter(DealDocument.id == document_id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Delete file from storage
        try:
            self.storage_service.delete_file(document.file_path)
        except Exception as e:
            print(f"Warning: Failed to delete file from storage: {str(e)}")

        # Delete database record
        self.db.delete(document)
        self.db.commit()

        return True

    def get_document(self, document_id: uuid.UUID) -> Optional[DealDocument]:
        """
        Get a single document by ID.

        Args:
            document_id: UUID of the document

        Returns:
            DealDocument object or None
        """
        return (
            self.db.query(DealDocument)
            .filter(DealDocument.id == document_id)
            .first()
        )
