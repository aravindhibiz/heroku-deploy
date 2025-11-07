"""
Note Routes

This module defines the RESTful API endpoints for Note operations.
Provides clean, well-documented routes for note management.

Key Features:
- RESTful API design
- Comprehensive OpenAPI documentation
- Input validation with Pydantic
- JWT authentication
- Error handling
- Contact-based note organization

Endpoints:
- GET /contact/{contact_id} - Get all notes for a contact
- GET /{note_id} - Get a specific note
- GET /author/{author_id} - Get all notes by an author
- GET /search - Search notes by content
- GET /recent - Get recent notes
- POST / - Create a new note
- PUT /{note_id} - Update a note
- DELETE /{note_id} - Delete a note
- GET /contact/{contact_id}/count - Get note count for a contact

Author: CRM System
Date: 2024
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user
from schemas.note import NoteCreate, NoteUpdate, NoteResponse
from models.user import UserProfile
from controllers.note_controller import NoteController


router = APIRouter(tags=["Notes"])


@router.get(
    "/contact/{contact_id}",
    response_model=List[NoteResponse],
    summary="Get notes for a contact",
    description="""
    Retrieve all notes associated with a specific contact.
    
    Notes are returned in descending order by creation date (newest first).
    Each note includes author information and timestamps.
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - List of notes with author information
    - Empty list if no notes exist for the contact
    
    **Errors:**
    - 404: Contact not found
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_notes_for_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.get_notes_by_contact(contact_id, current_user)


@router.get(
    "/author/{author_id}",
    response_model=List[NoteResponse],
    summary="Get notes by author",
    description="""
    Retrieve all notes created by a specific author.
    
    Notes are returned in descending order by creation date (newest first).
    Users can only view their own notes unless they have admin privileges.
    
    **Authorization:**
    - Requires valid JWT authentication
    - Users can only view their own notes
    
    **Returns:**
    - List of notes with contact information
    - Empty list if no notes exist
    
    **Errors:**
    - 403: Permission denied (viewing other user's notes)
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_notes_by_author(
    author_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.get_notes_by_author(author_id, current_user)


@router.get(
    "/search",
    response_model=List[NoteResponse],
    summary="Search notes",
    description="""
    Search notes by content or title.
    
    Performs case-insensitive search across note titles and content.
    Can be filtered by contact or author.
    
    **Query Parameters:**
    - q (required): Search term
    - contact_id (optional): Filter by contact
    - author_only (optional): Filter by current user's notes
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - List of matching notes in descending order by creation date
    - Empty list if no matches found
    
    **Errors:**
    - 400: Invalid search term
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def search_notes(
    q: str = Query(..., description="Search term", min_length=1),
    contact_id: Optional[UUID] = Query(None, description="Filter by contact"),
    author_only: bool = Query(False, description="Only search user's notes"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    # If author_only is True, pass current_user to filter by author
    # Otherwise, pass None to search all notes
    user_for_filter = current_user if author_only else None
    return controller.search_notes(q, contact_id=contact_id, current_user=user_for_filter)


@router.get(
    "/recent",
    response_model=List[NoteResponse],
    summary="Get recent notes",
    description="""
    Get the most recently created notes across all contacts.
    
    Useful for displaying activity feeds or recent updates.
    
    **Query Parameters:**
    - limit: Maximum number of notes to return (1-100, default: 10)
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - List of recent notes with author and contact information
    - Empty list if no notes exist
    
    **Errors:**
    - 400: Invalid limit value
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_recent_notes(
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of notes"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.get_recent_notes(limit, current_user)


@router.get(
    "/contact/{contact_id}/count",
    summary="Get note count for contact",
    description="""
    Get the total number of notes for a specific contact.
    
    Useful for displaying note counts in contact lists or summaries.
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - contact_id: The contact ID
    - note_count: Total number of notes
    
    **Errors:**
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_contact_note_count(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.get_contact_note_count(contact_id, current_user)


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get a specific note",
    description="""
    Retrieve a single note by its ID.
    
    Includes full note details with author and contact information.
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - Complete note data with relationships
    
    **Errors:**
    - 404: Note not found
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.get_note(note_id, current_user)


@router.post(
    "/",
    response_model=NoteResponse,
    status_code=201,
    summary="Create a note",
    description="""
    Create a new note for a contact.
    
    The note will be associated with the authenticated user as the author.
    Content is required and cannot be empty.
    
    **Request Body:**
    - title (optional): Note title
    - content (required): Note content (cannot be empty)
    - contact_id (required): ID of the associated contact
    
    **Authorization:**
    - Requires valid JWT authentication
    - User becomes the note author
    
    **Returns:**
    - Created note with author information (201 Created)
    
    **Errors:**
    - 404: Contact not found
    - 400: Validation error (empty content, etc.)
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def create_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.create_note(note, current_user)


@router.put(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Update a note",
    description="""
    Update an existing note.
    
    Only the note author can update the note.
    At least one field (title or content) must be provided.
    
    **Request Body:**
    - title (optional): Updated note title
    - content (optional): Updated note content (cannot be empty)
    
    **Authorization:**
    - Requires valid JWT authentication
    - Only the note author can update
    
    **Returns:**
    - Updated note with author information
    
    **Errors:**
    - 404: Note not found
    - 403: Permission denied (not the author)
    - 400: Validation error (no fields to update, empty content)
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def update_note(
    note_id: UUID,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.update_note(note_id, note_update, current_user)


@router.delete(
    "/{note_id}",
    summary="Delete a note",
    description="""
    Delete a note.
    
    Only the note author can delete the note.
    This action cannot be undone.
    
    **Authorization:**
    - Requires valid JWT authentication
    - Only the note author can delete
    
    **Returns:**
    - Success message
    
    **Errors:**
    - 404: Note not found
    - 403: Permission denied (not the author)
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def delete_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = NoteController(db)
    return controller.delete_note(note_id, current_user)


@router.get("/test/ping")
async def test_notes():
    """
    Test endpoint to verify the notes router is working.

    Returns:
        dict: Simple test response
    """
    return {"message": "Notes API is working", "status": "ok"}
