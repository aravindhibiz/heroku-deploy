"""
Company repository for data access operations.
Handles all database queries related to companies.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc

from .base_repository import BaseRepository
from ..models.company import Company


class CompanyRepository(BaseRepository[Company]):
    """
    Repository for Company entity.

    Provides specialized query methods for companies beyond the base CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize the company repository.

        Args:
            db: Database session
        """
        super().__init__(Company, db)

    def count(self, owner_id: Optional[UUID] = None) -> int:
        """
        Count companies with optional owner filtering.

        Args:
            owner_id: Optional filter by owner ID

        Returns:
            Number of companies matching the criteria
        """
        if owner_id:
            return super().count(filters={"owner_id": owner_id})
        return super().count()

    def get_with_relations(self, company_id: UUID) -> Optional[Company]:
        """
        Retrieve a company with all its relationships loaded.

        Args:
            company_id: UUID of the company

        Returns:
            Company with loaded relationships, or None if not found
        """
        return (
            self.db.query(Company)
            .options(
                joinedload(Company.owner),
                joinedload(Company.contacts),
                joinedload(Company.deals)
            )
            .filter(Company.id == company_id)
            .first()
        )

    def get_all_ordered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by_name: bool = True,
        load_relations: bool = True
    ) -> List[Company]:
        """
        Retrieve all companies with optional ordering and relations.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by_name: Whether to order by company name
            load_relations: Whether to load related entities

        Returns:
            List of companies
        """
        query = self.db.query(Company)

        if load_relations:
            query = query.options(
                joinedload(Company.owner),
                joinedload(Company.contacts),
                joinedload(Company.deals)
            )

        if order_by_name:
            query = query.order_by(asc(Company.name))
        else:
            query = query.order_by(desc(Company.created_at))

        return query.offset(skip).limit(limit).all()

    def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        load_relations: bool = True
    ) -> List[Company]:
        """
        Retrieve companies for a specific owner.

        Args:
            owner_id: UUID of the owner
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relations: Whether to load related entities

        Returns:
            List of companies for the owner
        """
        query = self.db.query(Company).filter(Company.owner_id == owner_id)

        if load_relations:
            query = query.options(
                joinedload(Company.owner),
                joinedload(Company.contacts),
                joinedload(Company.deals)
            )

        return (
            query
            .order_by(asc(Company.name))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_industry(
        self,
        industry: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Company]:
        """
        Retrieve companies in a specific industry.

        Args:
            industry: Industry name
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of companies in the industry
        """
        return (
            self.db.query(Company)
            .filter(Company.industry == industry)
            .order_by(asc(Company.name))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_by_name(
        self,
        search_term: str,
        *,
        skip: int = 0,
        limit: int = 100,
        owner_id: Optional[UUID] = None,
        load_relations: bool = True
    ) -> List[Company]:
        """
        Search companies by multiple fields: name, industry, location (city/state/country), and size.
        Uses case-insensitive partial matching across all fields.

        Args:
            search_term: Search term to match against multiple company fields
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_id: Optional filter by owner ID
            load_relations: Whether to load related entities

        Returns:
            List of matching companies
        """
        from sqlalchemy import or_

        search_pattern = f"%{search_term}%"

        # Search across multiple fields: name, industry, city, state, country, size
        query = self.db.query(Company).filter(
            or_(
                Company.name.ilike(search_pattern),
                Company.industry.ilike(search_pattern),
                Company.city.ilike(search_pattern),
                Company.state.ilike(search_pattern),
                Company.country.ilike(search_pattern),
                Company.size.ilike(search_pattern)
            )
        )

        if owner_id:
            query = query.filter(Company.owner_id == owner_id)

        if load_relations:
            query = query.options(
                joinedload(Company.owner),
                joinedload(Company.contacts),
                joinedload(Company.deals)
            )

        return (
            query
            .order_by(asc(Company.name))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_size(
        self,
        size: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Company]:
        """
        Retrieve companies of a specific size.

        Args:
            size: Company size (e.g., "Small", "Medium", "Large")
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of companies of the specified size
        """
        return (
            self.db.query(Company)
            .filter(Company.size == size)
            .order_by(asc(Company.name))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_industry(self, owner_id: Optional[UUID] = None) -> dict:
        """
        Count companies grouped by industry.

        Args:
            owner_id: Optional filter by owner ID

        Returns:
            Dictionary of industry: count pairs
        """
        from sqlalchemy import func

        query = self.db.query(
            Company.industry,
            func.count(Company.id).label('count')
        )

        if owner_id:
            query = query.filter(Company.owner_id == owner_id)

        results = query.group_by(Company.industry).all()

        return {industry: count for industry, count in results if industry}

    def count_by_size(self, owner_id: Optional[UUID] = None) -> dict:
        """
        Count companies grouped by size.

        Args:
            owner_id: Optional filter by owner ID

        Returns:
            Dictionary of size: count pairs
        """
        from sqlalchemy import func

        query = self.db.query(
            Company.size,
            func.count(Company.id).label('count')
        )

        if owner_id:
            query = query.filter(Company.owner_id == owner_id)

        results = query.group_by(Company.size).all()

        return {size: count for size, count in results if size}

    def get_recent_companies(
        self,
        *,
        limit: int = 10
    ) -> List[Company]:
        """
        Retrieve the most recently created companies.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent companies
        """
        return (
            self.db.query(Company)
            .options(
                joinedload(Company.owner),
                joinedload(Company.contacts),
                joinedload(Company.deals)
            )
            .order_by(desc(Company.created_at))
            .limit(limit)
            .all()
        )

    def count_recent(self, since_date, owner_id: Optional[UUID] = None) -> int:
        """
        Count companies created since a specific date.

        Args:
            since_date: Date to count from
            owner_id: Optional filter by owner ID

        Returns:
            Number of companies created since the date
        """
        from sqlalchemy import func

        query = self.db.query(func.count(Company.id)).filter(
            Company.created_at >= since_date
        )

        if owner_id:
            query = query.filter(Company.owner_id == owner_id)

        return query.scalar() or 0
