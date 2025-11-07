"""
Note Service Layer

This module provides business logic for Note management operations.
Implements the Service pattern for note-related functionality.

Key Features:
- Note CRUD operations with validation
- Contact validation
- Author authorization
- Business rule enforcement
- Error handling

Author: CRM System
Date: 2024
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from models.note import Note
from models.contact import Contact
from schemas.note import NoteCreate, NoteUpdate
from repositories.note_repository import NoteRepository


class NoteService:
    """
    Service class for Note business logic.

    This class implements business rules and orchestrates operations
    between controllers and repositories.

    Responsibilities:
    - Validate note data and business rules
    - Verify contact existence
    - Check author permissions
    - Orchestrate repository operations
    - Format responses with relationships
    """

    def __init__(self, db: Session):
        """
        Initialize the NoteService.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.repository = NoteRepository(db)

    def get_note_by_id(
        self,
        note_id: UUID,
        user_id: UUID
    ) -> Optional[Note]:
        """
        Get a note by ID.

        Args:
            note_id (UUID): The note ID to retrieve
            user_id (UUID): The requesting user ID (for future permission checks)

        Returns:
            Optional[Note]: The note if found, None otherwise
        """
        return self.repository.get_by_id(note_id, load_relationships=True)

    def get_notes_by_contact(
        self,
        contact_id: UUID,
        user_id: UUID
    ) -> List[Note]:
        """
        Get all notes for a contact.

        Args:
            contact_id (UUID): The contact ID to get notes for
            user_id (UUID): The requesting user ID (for future permission checks)

        Returns:
            List[Note]: List of notes for the contact

        Raises:
            ValueError: If contact does not exist
        """
        # Validate contact exists
        contact = self.db.query(Contact).filter(
            Contact.id == contact_id).first()
        if not contact:
            raise ValueError("Contact not found")

        return self.repository.get_by_contact(
            contact_id,
            load_author=True,
            order_by_newest=True
        )

    def get_notes_by_author(
        self,
        author_id: UUID,
        user_id: UUID
    ) -> List[Note]:
        """
        Get all notes created by an author.

        Args:
            author_id (UUID): The author ID to get notes for
            user_id (UUID): The requesting user ID (for permission checks)

        Returns:
            List[Note]: List of notes created by the author

        Raises:
            PermissionError: If user is not the author and doesn't have admin rights
        """
        # For now, users can only view their own notes
        # In the future, this can be extended with role-based permissions
        if author_id != user_id:
            raise PermissionError("You can only view your own notes")

        return self.repository.get_by_author(
            author_id,
            load_contact=True,
            order_by_newest=True
        )

    def create_note(
        self,
        note_data: NoteCreate,
        user_id: UUID
    ) -> Note:
        """
        Create a new note.

        Args:
            note_data (NoteCreate): The note data to create
            user_id (UUID): The ID of the user creating the note

        Returns:
            Note: The created note with author information

        Raises:
            ValueError: If contact does not exist
            ValueError: If required fields are missing
        """
        # Validate contact exists
        contact = self.db.query(Contact).filter(
            Contact.id == note_data.contact_id
        ).first()
        if not contact:
            raise ValueError("Contact not found")

        # Validate content is not empty
        if not note_data.content or not note_data.content.strip():
            raise ValueError("Note content cannot be empty")

        # Create note
        new_note = Note(
            title=note_data.title,
            content=note_data.content.strip(),
            contact_id=note_data.contact_id,
            created_by=user_id
        )

        created_note = self.repository.create(new_note)

        # Reload with relationships
        return self.repository.get_by_id(created_note.id, load_relationships=True)

    def update_note(
        self,
        note_id: UUID,
        note_data: NoteUpdate,
        user_id: UUID
    ) -> Note:
        """
        Update an existing note.

        Args:
            note_id (UUID): The ID of the note to update
            note_data (NoteUpdate): The updated note data
            user_id (UUID): The ID of the user updating the note

        Returns:
            Note: The updated note with author information

        Raises:
            ValueError: If note does not exist
            PermissionError: If user is not the note author
            ValueError: If update data is invalid
        """
        # Get existing note
        note = self.repository.get_by_id(note_id, load_relationships=False)
        if not note:
            raise ValueError("Note not found")

        # Check authorization - only author can update
        if note.created_by != user_id:
            raise PermissionError("You can only edit your own notes")

        # Validate at least one field is being updated
        if note_data.title is None and note_data.content is None:
            raise ValueError("No fields to update")

        # Update fields
        if note_data.title is not None:
            note.title = note_data.title

        if note_data.content is not None:
            # Validate content is not empty
            if not note_data.content.strip():
                raise ValueError("Note content cannot be empty")
            note.content = note_data.content.strip()

        updated_note = self.repository.update(note)

        # Reload with relationships
        return self.repository.get_by_id(updated_note.id, load_relationships=True)

    def delete_note(
        self,
        note_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Delete a note.

        Args:
            note_id (UUID): The ID of the note to delete
            user_id (UUID): The ID of the user deleting the note

        Raises:
            ValueError: If note does not exist
            PermissionError: If user is not the note author
        """
        # Get existing note
        note = self.repository.get_by_id(note_id, load_relationships=False)
        if not note:
            raise ValueError("Note not found")

        # Check authorization - only author can delete
        if note.created_by != user_id:
            raise PermissionError("You can only delete your own notes")

        self.repository.delete(note)

    def search_notes(
        self,
        search_term: str,
        contact_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> List[Note]:
        """
        Search notes by content or title.

        Args:
            search_term (str): The term to search for
            contact_id (Optional[UUID]): Filter by contact if provided
            user_id (Optional[UUID]): Filter by author if provided

        Returns:
            List[Note]: List of matching notes

        Raises:
            ValueError: If search term is empty
        """
        if not search_term or not search_term.strip():
            raise ValueError("Search term cannot be empty")

        return self.repository.search_by_content(
            search_term.strip(),
            contact_id=contact_id,
            author_id=user_id,
            load_relationships=True
        )

    def get_recent_notes(
        self,
        limit: int = 10
    ) -> List[Note]:
        """
        Get most recent notes.

        Args:
            limit (int): Maximum number of notes to return

        Returns:
            List[Note]: List of recent notes
        """
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")

        return self.repository.get_recent_notes(
            limit=limit,
            load_relationships=True
        )

    def get_contact_note_count(self, contact_id: UUID) -> int:
        """
        Get the count of notes for a contact.

        Args:
            contact_id (UUID): The contact ID to count notes for

        Returns:
            int: Number of notes for the contact
        """
        return self.repository.count_by_contact(contact_id)

    def get_author_note_count(self, author_id: UUID) -> int:
        """
        Get the count of notes created by an author.

        Args:
            author_id (UUID): The author ID to count notes for

        Returns:
            int: Number of notes created by the author
        """
        return self.repository.count_by_author(author_id)

    def format_note_response(self, note: Note) -> dict:
        """
        Format a note object for API response.

        Args:
            note (Note): The note to format

        Returns:
            dict: Formatted note data with author information
        """
        return {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "contact_id": note.contact_id,
            "created_by": note.created_by,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
            "author": {
                "id": str(note.author.id),
                "first_name": note.author.first_name,
                "last_name": note.author.last_name,
                "email": note.author.email
            } if note.author else None,
            "contact": {
                "id": str(note.contact.id),
                "first_name": note.contact.first_name,
                "last_name": note.contact.last_name,
                "email": note.contact.email
            } if hasattr(note, 'contact') and note.contact else None
        }
