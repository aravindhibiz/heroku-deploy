from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID
from core.database import get_db
from core.auth import get_current_user
from models.user import UserProfile
from models.note import Note
from models.contact import Contact
from schemas.note import NoteCreate, NoteUpdate, NoteResponse

router = APIRouter()


@router.get("/contact/{contact_id}", response_model=List[NoteResponse])
async def get_contact_notes(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Verify contact exists and user has access
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # For now, allow access if user can view contacts
    # In future, implement proper ownership/team access control

    notes = db.query(Note).options(
        joinedload(Note.author)
    ).filter(
        Note.contact_id == contact_id
    ).order_by(Note.created_at.desc()).all()

    # Format the response to include author info
    formatted_notes = []
    for note in notes:
        note_dict = {
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
            } if note.author else None
        }
        formatted_notes.append(note_dict)

    return formatted_notes


@router.post("/", response_model=NoteResponse)
async def create_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Verify contact exists and user has access
    contact = db.query(Contact).filter(Contact.id == note.contact_id).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Create the note
    db_note = Note(
        title=note.title,
        content=note.content,
        contact_id=note.contact_id,
        created_by=current_user.id
    )

    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    # Load with author info
    note_with_author = db.query(Note).options(
        joinedload(Note.author)
    ).filter(Note.id == db_note.id).first()

    return {
        "id": note_with_author.id,
        "title": note_with_author.title,
        "content": note_with_author.content,
        "contact_id": note_with_author.contact_id,
        "created_by": note_with_author.created_by,
        "created_at": note_with_author.created_at,
        "updated_at": note_with_author.updated_at,
        "author": {
            "id": str(note_with_author.author.id),
            "first_name": note_with_author.author.first_name,
            "last_name": note_with_author.author.last_name,
            "email": note_with_author.author.email
        } if note_with_author.author else None
    }


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: UUID,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Find the note
    db_note = db.query(Note).filter(Note.id == note_id).first()
    if not db_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check if user is the author (for now, only author can edit)
    if db_note.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own notes"
        )

    # Update the note
    if note_update.title is not None:
        db_note.title = note_update.title
    if note_update.content is not None:
        db_note.content = note_update.content

    db.commit()
    db.refresh(db_note)

    # Load with author info
    note_with_author = db.query(Note).options(
        joinedload(Note.author)
    ).filter(Note.id == db_note.id).first()

    return {
        "id": note_with_author.id,
        "title": note_with_author.title,
        "content": note_with_author.content,
        "contact_id": note_with_author.contact_id,
        "created_by": note_with_author.created_by,
        "created_at": note_with_author.created_at,
        "updated_at": note_with_author.updated_at,
        "author": {
            "id": str(note_with_author.author.id),
            "first_name": note_with_author.author.first_name,
            "last_name": note_with_author.author.last_name,
            "email": note_with_author.author.email
        } if note_with_author.author else None
    }


@router.delete("/{note_id}")
async def delete_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Find the note
    db_note = db.query(Note).filter(Note.id == note_id).first()
    if not db_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check if user is the author (for now, only author can delete)
    if db_note.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own notes"
        )

    db.delete(db_note)
    db.commit()

    return {"message": "Note deleted successfully"}
