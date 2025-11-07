"""
Base repository with common CRUD operations.
All specific repositories should inherit from this base class.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing common database operations.

    This class implements the Repository pattern to abstract database operations
    and provide a clean interface for data access.
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize the repository.

        Args:
            model: The SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def create(self, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record in the database.

        Args:
            obj_in: Dictionary of attributes for the new record

        Returns:
            The created database object

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get(self, id: UUID) -> Optional[ModelType]:
        """
        Retrieve a record by ID.

        Args:
            id: The UUID of the record to retrieve

        Returns:
            The database object if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """
        Retrieve multiple records with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value pairs to filter by
            order_by: SQLAlchemy order_by clause

        Returns:
            List of database objects
        """
        query = self.db.query(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        if order_by is not None:
            query = query.order_by(order_by)

        return query.offset(skip).limit(limit).all()

    def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        Update a record in the database.

        Args:
            db_obj: The existing database object to update
            obj_in: Dictionary of attributes to update

        Returns:
            The updated database object

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def delete(self, *, id: UUID) -> bool:
        """
        Delete a record from the database.

        Args:
            id: The UUID of the record to delete

        Returns:
            True if deletion was successful, False if record not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            obj = self.get(id)
            if obj:
                self.db.delete(obj)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def exists(self, id: UUID) -> bool:
        """
        Check if a record exists in the database.

        Args:
            id: The UUID of the record to check

        Returns:
            True if record exists, False otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first() is not None

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in the database with optional filtering.

        Args:
            filters: Dictionary of field:value pairs to filter by

        Returns:
            Number of records matching the criteria
        """
        query = self.db.query(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        return query.count()
