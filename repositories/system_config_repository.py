"""
System Configuration Repository Layer

This module provides data access operations for SystemConfiguration entities.
Implements the Repository pattern for database interactions.

Key Features:
- CRUD operations for system configurations
- Category-based queries
- Configuration validation
- Export/Import support
- Bulk update operations
- Efficient querying with SQLAlchemy

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import desc
from sqlalchemy.orm import Session
from models.system_config import SystemConfiguration


class SystemConfigRepository:
    """
    Repository class for SystemConfiguration entity database operations.

    This class encapsulates all database queries and operations for system configurations,
    providing a clean interface for the service layer.

    Responsibilities:
    - Execute database queries for configurations
    - Handle filtering by category
    - Manage configuration CRUD operations
    - Support bulk operations
    - Provide grouped queries
    """

    def __init__(self, db: Session):
        """
        Initialize the SystemConfigRepository.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db

    def get_all(
        self,
        category: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[SystemConfiguration]:
        """
        Get all system configurations with optional filtering.

        Args:
            category (Optional[str]): Filter by category
            include_inactive (bool): Whether to include inactive configs

        Returns:
            List[SystemConfiguration]: List of configurations
        """
        query = self.db.query(SystemConfiguration)

        if not include_inactive:
            query = query.filter(SystemConfiguration.is_active == True)

        if category:
            query = query.filter(SystemConfiguration.category == category)

        return query.order_by(
            SystemConfiguration.category,
            SystemConfiguration.key
        ).all()

    def get_by_id(self, config_id: UUID) -> Optional[SystemConfiguration]:
        """
        Get a configuration by its ID.

        Args:
            config_id (UUID): The configuration ID

        Returns:
            Optional[SystemConfiguration]: The configuration if found
        """
        return self.db.query(SystemConfiguration).filter(
            SystemConfiguration.id == config_id
        ).first()

    def get_by_key(self, key: str) -> Optional[SystemConfiguration]:
        """
        Get a configuration by its key.

        Args:
            key (str): The configuration key

        Returns:
            Optional[SystemConfiguration]: The configuration if found
        """
        return self.db.query(SystemConfiguration).filter(
            SystemConfiguration.key == key
        ).first()

    def get_active_by_key(self, key: str) -> Optional[SystemConfiguration]:
        """
        Get an active configuration by its key.

        Args:
            key (str): The configuration key

        Returns:
            Optional[SystemConfiguration]: The active configuration if found
        """
        return self.db.query(SystemConfiguration).filter(
            SystemConfiguration.key == key,
            SystemConfiguration.is_active == True
        ).first()

    def get_by_category(
        self,
        category: str,
        include_inactive: bool = False
    ) -> List[SystemConfiguration]:
        """
        Get all configurations in a category.

        Args:
            category (str): The category to filter by
            include_inactive (bool): Whether to include inactive configs

        Returns:
            List[SystemConfiguration]: List of configurations in the category
        """
        query = self.db.query(SystemConfiguration).filter(
            SystemConfiguration.category == category
        )

        if not include_inactive:
            query = query.filter(SystemConfiguration.is_active == True)

        return query.order_by(SystemConfiguration.key).all()

    def get_grouped_by_category(
        self,
        include_inactive: bool = False
    ) -> Dict[str, List[SystemConfiguration]]:
        """
        Get configurations grouped by category.

        Args:
            include_inactive (bool): Whether to include inactive configs

        Returns:
            Dict[str, List[SystemConfiguration]]: Configurations grouped by category
        """
        configurations = self.get_all(include_inactive=include_inactive)

        grouped = {}
        for config in configurations:
            if config.category not in grouped:
                grouped[config.category] = []
            grouped[config.category].append(config)

        return grouped

    def get_as_dict(
        self,
        category: Optional[str] = None,
        nested: bool = True
    ) -> Dict[str, Any]:
        """
        Get configurations as a dictionary.

        Args:
            category (Optional[str]): Filter by category
            nested (bool): Whether to create nested structure (general.currency -> {general: {currency: "USD"}})

        Returns:
            Dict[str, Any]: Configuration key-value pairs
        """
        configurations = self.get_all(
            category=category, include_inactive=False)

        result = {}
        for config in configurations:
            if nested:
                # Create nested structure
                key_parts = config.key.split('.')
                if len(key_parts) == 2:
                    cat, field = key_parts
                    if cat not in result:
                        result[cat] = {}
                    result[cat][field] = config.value
                else:
                    result[config.key] = config.value
            else:
                # Flat structure
                result[config.key] = config.value

        return result

    def create(self, configuration: SystemConfiguration) -> SystemConfiguration:
        """
        Create a new configuration.

        Args:
            configuration (SystemConfiguration): The configuration to create

        Returns:
            SystemConfiguration: The created configuration
        """
        self.db.add(configuration)
        self.db.commit()
        self.db.refresh(configuration)
        return configuration

    def update(self, configuration: SystemConfiguration) -> SystemConfiguration:
        """
        Update an existing configuration.

        Args:
            configuration (SystemConfiguration): The configuration with updated values

        Returns:
            SystemConfiguration: The updated configuration
        """
        self.db.commit()
        self.db.refresh(configuration)
        return configuration

    def delete(self, configuration: SystemConfiguration) -> None:
        """
        Hard delete a configuration.

        Args:
            configuration (SystemConfiguration): The configuration to delete
        """
        self.db.delete(configuration)
        self.db.commit()

    def soft_delete(self, configuration: SystemConfiguration) -> SystemConfiguration:
        """
        Soft delete a configuration by setting is_active to False.

        Args:
            configuration (SystemConfiguration): The configuration to soft delete

        Returns:
            SystemConfiguration: The updated configuration
        """
        configuration.is_active = False
        return self.update(configuration)

    def bulk_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> tuple[int, List[str]]:
        """
        Update multiple configurations at once.

        Args:
            updates (List[Dict[str, Any]]): List of updates with 'key' and 'value'

        Returns:
            tuple[int, List[str]]: (updated_count, list of errors)
        """
        updated_count = 0
        errors = []

        for update in updates:
            key = update.get('key')
            value = update.get('value')

            if not key:
                errors.append("Missing configuration key")
                continue

            config = self.get_by_key(key)
            if config:
                config.value = value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {key}")

        if updated_count > 0:
            self.db.commit()

        return updated_count, errors

    def create_or_update(
        self,
        key: str,
        value: Any,
        category: str,
        description: Optional[str] = None
    ) -> SystemConfiguration:
        """
        Create a new configuration or update if exists.

        Args:
            key (str): Configuration key
            value (Any): Configuration value
            category (str): Configuration category
            description (Optional[str]): Configuration description

        Returns:
            SystemConfiguration: The created or updated configuration
        """
        config = self.get_by_key(key)

        if config:
            config.value = value
            if description:
                config.description = description
            return self.update(config)
        else:
            new_config = SystemConfiguration(
                key=key,
                value=value,
                category=category,
                description=description
            )
            return self.create(new_config)

    def get_categories(self) -> List[str]:
        """
        Get list of all unique categories.

        Returns:
            List[str]: List of category names
        """
        categories = self.db.query(SystemConfiguration.category).filter(
            SystemConfiguration.is_active == True
        ).distinct().all()

        return [cat[0] for cat in categories]

    def count_by_category(self, category: str) -> int:
        """
        Count configurations in a category.

        Args:
            category (str): The category to count

        Returns:
            int: Number of configurations in the category
        """
        return self.db.query(SystemConfiguration).filter(
            SystemConfiguration.category == category,
            SystemConfiguration.is_active == True
        ).count()

    def get_export_data(self) -> Dict[str, Any]:
        """
        Get all configurations formatted for export.

        Returns:
            Dict[str, Any]: Export data with metadata
        """
        configurations = self.get_all(include_inactive=False)

        export_data = {}
        for config in configurations:
            export_data[config.key] = {
                "value": config.value,
                "category": config.category,
                "description": config.description
            }

        return export_data

    def activate(self, configuration: SystemConfiguration) -> SystemConfiguration:
        """
        Activate a configuration.

        Args:
            configuration (SystemConfiguration): The configuration to activate

        Returns:
            SystemConfiguration: The activated configuration
        """
        configuration.is_active = True
        return self.update(configuration)

    def deactivate(self, configuration: SystemConfiguration) -> SystemConfiguration:
        """
        Deactivate a configuration.

        Args:
            configuration (SystemConfiguration): The configuration to deactivate

        Returns:
            SystemConfiguration: The deactivated configuration
        """
        configuration.is_active = False
        return self.update(configuration)
