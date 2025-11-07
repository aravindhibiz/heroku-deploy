"""
Note Repository Layer

This module provides data access operations for Note entities.
Implements the Repository pattern for database interactions with notes.

Key Features:
- CRUD operations for notes
- Contact-based queries
- Author-based queries
- Eager loading of relationships (author, contact)
- Efficient querying with SQLAlchemy

Author: CRM System
Date: 2024
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from ..models.note import Note


class NoteRepository:
    """
    Repository class for Note entity database operations.

    This class encapsulates all database queries and operations for notes,
    providing a clean interface for the service layer.

    Responsibilities:
    - Execute database queries for notes
    - Handle relationship loading (author, contact)
    - Provide filtered queries by contact, author, etc.
    - Manage note CRUD operations
    """

    def __init__(self, db: Session):
        """
        Initialize the NoteRepository.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db

    def get_by_id(
        self,
        note_id: UUID,
        load_relationships: bool = True
    ) -> Optional[Note]:
        """
        Get a note by its ID.

        Args:
            note_id (UUID): The note ID to search for
            load_relationships (bool): Whether to eager load author and contact

        Returns:
            Optional[Note]: The note if found, None otherwise
        """
        query = self.db.query(Note)

        if load_relationships:
            query = query.options(
                joinedload(Note.author),
                joinedload(Note.contact)
            )

        return query.filter(Note.id == note_id).first()

    def get_by_contact(
        self,
        contact_id: UUID,
        load_author: bool = True,
        order_by_newest: bool = True
    ) -> List[Note]:
        """
        Get all notes for a specific contact.

        Args:
            contact_id (UUID): The contact ID to filter by
            load_author (bool): Whether to eager load author information
            order_by_newest (bool): Whether to order by newest first

        Returns:
            List[Note]: List of notes for the contact
        """
        query = self.db.query(Note)

        if load_author:
            query = query.options(joinedload(Note.author))

        query = query.filter(Note.contact_id == contact_id)

        if order_by_newest:
            query = query.order_by(desc(Note.created_at))
        else:
            query = query.order_by(Note.created_at)

        return query.all()

    def get_by_author(
        self,
        author_id: UUID,
        load_contact: bool = True,
        order_by_newest: bool = True
    ) -> List[Note]:
        """
        Get all notes created by a specific author.

        Args:
            author_id (UUID): The author (user) ID to filter by
            load_contact (bool): Whether to eager load contact information
            order_by_newest (bool): Whether to order by newest first

        Returns:
            List[Note]: List of notes created by the author
        """
        query = self.db.query(Note)

        if load_contact:
            query = query.options(joinedload(Note.contact))

        query = query.filter(Note.created_by == author_id)

        if order_by_newest:
            query = query.order_by(desc(Note.created_at))
        else:
            query = query.order_by(Note.created_at)

        return query.all()

    def create(self, note: Note) -> Note:
        """
        Create a new note.

        Args:
            note (Note): The note object to create

        Returns:
            Note: The created note with generated ID and timestamps
        """
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def update(self, note: Note) -> Note:
        """
        Update an existing note.

        Args:
            note (Note): The note object with updated values

        Returns:
            Note: The updated note
        """
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete(self, note: Note) -> None:
        """
        Delete a note.

        Args:
            note (Note): The note object to delete
        """
        self.db.delete(note)
        self.db.commit()

    def count_by_contact(self, contact_id: UUID) -> int:
        """
        Count notes for a specific contact.

        Args:
            contact_id (UUID): The contact ID to count notes for

        Returns:
            int: Number of notes for the contact
        """
        return self.db.query(Note).filter(
            Note.contact_id == contact_id
        ).count()

    def count_by_author(self, author_id: UUID) -> int:
        """
        Count notes created by a specific author.

        Args:
            author_id (UUID): The author ID to count notes for

        Returns:
            int: Number of notes created by the author
        """
        return self.db.query(Note).filter(
            Note.created_by == author_id
        ).count()

    def search_by_content(
        self,
        search_term: str,
        contact_id: Optional[UUID] = None,
        author_id: Optional[UUID] = None,
        load_relationships: bool = True
    ) -> List[Note]:
        """
        Search notes by content or title.

        Args:
            search_term (str): The term to search for
            contact_id (Optional[UUID]): Filter by contact if provided
            author_id (Optional[UUID]): Filter by author if provided
            load_relationships (bool): Whether to eager load relationships

        Returns:
            List[Note]: List of matching notes
        """
        query = self.db.query(Note)

        if load_relationships:
            query = query.options(
                joinedload(Note.author),
                joinedload(Note.contact)
            )

        # Search in title or content
        search_filter = Note.content.ilike(f"%{search_term}%")
        if Note.title:
            search_filter = search_filter | Note.title.ilike(
                f"%{search_term}%")

        query = query.filter(search_filter)

        if contact_id:
            query = query.filter(Note.contact_id == contact_id)

        if author_id:
            query = query.filter(Note.created_by == author_id)

        return query.order_by(desc(Note.created_at)).all()

    def get_recent_notes(
        self,
        limit: int = 10,
        load_relationships: bool = True
    ) -> List[Note]:
        """
        Get most recent notes across all contacts.

        Args:
            limit (int): Maximum number of notes to return
            load_relationships (bool): Whether to eager load relationships

        Returns:
            List[Note]: List of recent notes
        """
        query = self.db.query(Note)

        if load_relationships:
            query = query.options(
                joinedload(Note.author),
                joinedload(Note.contact)
            )

        return query.order_by(desc(Note.created_at)).limit(limit).all()
