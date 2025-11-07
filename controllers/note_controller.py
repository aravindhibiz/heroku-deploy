"""
Note Controller Layer

This module provides HTTP request handling for Note operations.
Implements the Controller pattern for note management.

Key Features:
- HTTP request/response handling
- Error translation to HTTP exceptions
- Input validation
- Response formatting
- Authorization checks

Author: CRM System
Date: 2024
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from ..schemas.note import NoteCreate, NoteUpdate, NoteResponse
from ..models.user import UserProfile
from ..services.note_service import NoteService


class NoteController:
    """
    Controller class for Note HTTP operations.

    This class handles HTTP requests, translates service exceptions
    to appropriate HTTP responses, and formats data for the API.

    Responsibilities:
    - Handle HTTP request/response cycle
    - Translate service errors to HTTP exceptions
    - Validate input data
    - Format responses
    - Enforce authorization
    """

    def __init__(self, db: Session):
        """
        Initialize the NoteController.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.service = NoteService(db)

    def get_note(
        self,
        note_id: UUID,
        current_user: UserProfile
    ) -> dict:
        """
        Get a note by ID.

        Args:
            note_id (UUID): The note ID to retrieve
            current_user (UserProfile): The authenticated user

        Returns:
            dict: Formatted note data

        Raises:
            HTTPException: 404 if note not found
        """
        try:
            note = self.service.get_note_by_id(note_id, current_user.id)

            if not note:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Note not found"
                )

            return self.service.format_note_response(note)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve note: {str(e)}"
            )

    def get_notes_by_contact(
        self,
        contact_id: UUID,
        current_user: UserProfile
    ) -> List[dict]:
        """
        Get all notes for a contact.

        Args:
            contact_id (UUID): The contact ID to get notes for
            current_user (UserProfile): The authenticated user

        Returns:
            List[dict]: List of formatted note data

        Raises:
            HTTPException: 404 if contact not found
            HTTPException: 500 for internal errors
        """
        try:
            notes = self.service.get_notes_by_contact(
                contact_id, current_user.id)
            return [self.service.format_note_response(note) for note in notes]

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve notes: {str(e)}"
            )

    def get_notes_by_author(
        self,
        author_id: UUID,
        current_user: UserProfile
    ) -> List[dict]:
        """
        Get all notes created by an author.

        Args:
            author_id (UUID): The author ID to get notes for
            current_user (UserProfile): The authenticated user

        Returns:
            List[dict]: List of formatted note data

        Raises:
            HTTPException: 403 if permission denied
            HTTPException: 500 for internal errors
        """
        try:
            notes = self.service.get_notes_by_author(
                author_id, current_user.id)
            return [self.service.format_note_response(note) for note in notes]

        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve notes: {str(e)}"
            )

    def create_note(
        self,
        note_data: NoteCreate,
        current_user: UserProfile
    ) -> dict:
        """
        Create a new note.

        Args:
            note_data (NoteCreate): The note data to create
            current_user (UserProfile): The authenticated user

        Returns:
            dict: Formatted created note data

        Raises:
            HTTPException: 404 if contact not found
            HTTPException: 400 for validation errors
            HTTPException: 500 for internal errors
        """
        try:
            note = self.service.create_note(note_data, current_user.id)
            return self.service.format_note_response(note)

        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create note: {str(e)}"
            )

    def update_note(
        self,
        note_id: UUID,
        note_data: NoteUpdate,
        current_user: UserProfile
    ) -> dict:
        """
        Update an existing note.

        Args:
            note_id (UUID): The ID of the note to update
            note_data (NoteUpdate): The updated note data
            current_user (UserProfile): The authenticated user

        Returns:
            dict: Formatted updated note data

        Raises:
            HTTPException: 404 if note not found
            HTTPException: 403 if permission denied
            HTTPException: 400 for validation errors
            HTTPException: 500 for internal errors
        """
        try:
            note = self.service.update_note(
                note_id, note_data, current_user.id)
            return self.service.format_note_response(note)

        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update note: {str(e)}"
            )

    def delete_note(
        self,
        note_id: UUID,
        current_user: UserProfile
    ) -> dict:
        """
        Delete a note.

        Args:
            note_id (UUID): The ID of the note to delete
            current_user (UserProfile): The authenticated user

        Returns:
            dict: Success message

        Raises:
            HTTPException: 404 if note not found
            HTTPException: 403 if permission denied
            HTTPException: 500 for internal errors
        """
        try:
            self.service.delete_note(note_id, current_user.id)
            return {"message": "Note deleted successfully"}

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete note: {str(e)}"
            )

    def search_notes(
        self,
        search_term: str,
        contact_id: Optional[UUID] = None,
        current_user: Optional[UserProfile] = None
    ) -> List[dict]:
        """
        Search notes by content or title.

        Args:
            search_term (str): The term to search for
            contact_id (Optional[UUID]): Filter by contact if provided
            current_user (Optional[UserProfile]): The authenticated user

        Returns:
            List[dict]: List of formatted matching notes

        Raises:
            HTTPException: 400 for validation errors
            HTTPException: 500 for internal errors
        """
        try:
            user_id = current_user.id if current_user else None
            notes = self.service.search_notes(
                search_term,
                contact_id=contact_id,
                user_id=user_id
            )
            return [self.service.format_note_response(note) for note in notes]

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to search notes: {str(e)}"
            )

    def get_recent_notes(
        self,
        limit: int = 10,
        current_user: Optional[UserProfile] = None
    ) -> List[dict]:
        """
        Get most recent notes.

        Args:
            limit (int): Maximum number of notes to return
            current_user (Optional[UserProfile]): The authenticated user

        Returns:
            List[dict]: List of formatted recent notes

        Raises:
            HTTPException: 400 for validation errors
            HTTPException: 500 for internal errors
        """
        try:
            notes = self.service.get_recent_notes(limit)
            return [self.service.format_note_response(note) for note in notes]

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve recent notes: {str(e)}"
            )

    def get_contact_note_count(
        self,
        contact_id: UUID,
        current_user: UserProfile
    ) -> dict:
        """
        Get the count of notes for a contact.

        Args:
            contact_id (UUID): The contact ID to count notes for
            current_user (UserProfile): The authenticated user

        Returns:
            dict: Count information
        """
        try:
            count = self.service.get_contact_note_count(contact_id)
            return {
                "contact_id": str(contact_id),
                "note_count": count
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to count notes: {str(e)}"
            )
