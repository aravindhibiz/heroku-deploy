"""
System Configuration Service Layer

This module provides business logic for system configuration management.
Handles configuration defaults, validation, schema generation, and business rules.

Key Features:
- Default configuration initialization
- Configuration validation (email, integer, boolean)
- Schema generation with categories
- Configuration value retrieval with fallbacks
- Bulk operations
- Export/import support

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import re
from datetime import datetime
from sqlalchemy.orm import Session

from models.system_config import SystemConfiguration
from repositories.system_config_repository import SystemConfigRepository


# Default configuration values organized by category
DEFAULT_CONFIGURATIONS = {
    # General Settings
    "general.company_name": {
        "value": "My Company",
        "category": "general",
        "description": "Company name displayed throughout the system"
    },
    "general.company_email": {
        "value": "info@company.com",
        "category": "general",
        "description": "Primary company email address"
    },
    "general.company_phone": {
        "value": "+1234567890",
        "category": "general",
        "description": "Company contact phone number"
    },
    "general.company_address": {
        "value": "123 Business St, City, Country",
        "category": "general",
        "description": "Company physical address"
    },
    "general.timezone": {
        "value": "UTC",
        "category": "general",
        "description": "Default timezone for the system"
    },
    "general.date_format": {
        "value": "YYYY-MM-DD",
        "category": "general",
        "description": "Date format used throughout the system"
    },
    "general.time_format": {
        "value": "24h",
        "category": "general",
        "description": "Time format (12h or 24h)"
    },
    "general.currency": {
        "value": "USD",
        "category": "general",
        "description": "Default currency for financial data"
    },
    "general.language": {
        "value": "en",
        "category": "general",
        "description": "Default language for the system"
    },

    # Sales Settings
    "sales.default_pipeline_stage": {
        "value": "lead",
        "category": "sales",
        "description": "Default stage for new deals"
    },
    "sales.deal_currency": {
        "value": "USD",
        "category": "sales",
        "description": "Default currency for deals"
    },
    "sales.require_deal_value": {
        "value": False,
        "category": "sales",
        "description": "Whether deal value is required"
    },
    "sales.auto_progress_deals": {
        "value": False,
        "category": "sales",
        "description": "Automatically progress deals through pipeline"
    },
    "sales.deal_inactivity_warning_days": {
        "value": 30,
        "category": "sales",
        "description": "Days of inactivity before warning"
    },
    "sales.lead_scoring_enabled": {
        "value": True,
        "category": "sales",
        "description": "Enable lead scoring system"
    },
    "sales.opportunity_auto_close_days": {
        "value": 90,
        "category": "sales",
        "description": "Days before automatically closing stale opportunities"
    },

    # Notification Settings
    "notifications.email_notifications": {
        "value": True,
        "category": "notifications",
        "description": "Enable email notifications"
    },
    "notifications.deal_update_notifications": {
        "value": True,
        "category": "notifications",
        "description": "Notify users of deal updates"
    },
    "notifications.task_reminders": {
        "value": True,
        "category": "notifications",
        "description": "Send task reminder notifications"
    },
    "notifications.weekly_reports": {
        "value": False,
        "category": "notifications",
        "description": "Send weekly performance reports"
    },
    "notifications.system_alerts": {
        "value": True,
        "category": "notifications",
        "description": "Enable system-wide alerts"
    },
    "notifications.lead_assignment_alerts": {
        "value": True,
        "category": "notifications",
        "description": "Notify users when leads are assigned"
    },
    "notifications.quota_achievement_alerts": {
        "value": True,
        "category": "notifications",
        "description": "Alert users when quotas are achieved"
    },

    # Security Settings
    "security.password_complexity": {
        "value": "medium",
        "category": "security",
        "description": "Password complexity requirement (low, medium, high)"
    },
    "security.min_password_length": {
        "value": 8,
        "category": "security",
        "description": "Minimum password length"
    },
    "security.two_factor_auth": {
        "value": False,
        "category": "security",
        "description": "Require two-factor authentication"
    },
    "security.session_timeout_minutes": {
        "value": 60,
        "category": "security",
        "description": "Session timeout in minutes"
    },
    "security.max_login_attempts": {
        "value": 5,
        "category": "security",
        "description": "Maximum failed login attempts before lockout"
    },
    "security.lockout_duration_minutes": {
        "value": 30,
        "category": "security",
        "description": "Account lockout duration in minutes"
    },
    "security.data_encryption_at_rest": {
        "value": True,
        "category": "security",
        "description": "Enable data encryption at rest"
    },
    "security.audit_log_retention_days": {
        "value": 90,
        "category": "security",
        "description": "Days to retain audit logs"
    },

    # Backup Settings
    "backup.enable_automatic_backups": {
        "value": True,
        "category": "backup",
        "description": "Enable automatic database backups"
    },
    "backup.backup_frequency": {
        "value": "daily",
        "category": "backup",
        "description": "Backup frequency (hourly, daily, weekly)"
    },
    "backup.backup_retention_days": {
        "value": 30,
        "category": "backup",
        "description": "Days to retain backup files"
    },
    "backup.backup_location": {
        "value": "/backups",
        "category": "backup",
        "description": "Backup storage location"
    },
    "backup.compress_backups": {
        "value": True,
        "category": "backup",
        "description": "Compress backup files"
    },

    # Integration Settings
    "integrations.email_service_provider": {
        "value": "smtp",
        "category": "integrations",
        "description": "Email service provider (smtp, sendgrid, mailgun)"
    },
    "integrations.calendar_integration": {
        "value": "none",
        "category": "integrations",
        "description": "Calendar integration (none, google, outlook)"
    },
    "integrations.crm_sync_enabled": {
        "value": False,
        "category": "integrations",
        "description": "Enable external CRM synchronization"
    },
    "integrations.api_rate_limit": {
        "value": 1000,
        "category": "integrations",
        "description": "API rate limit per hour"
    },

    # Performance Settings
    "performance.enable_caching": {
        "value": True,
        "category": "performance",
        "description": "Enable system caching"
    },
    "performance.cache_ttl_seconds": {
        "value": 3600,
        "category": "performance",
        "description": "Cache time-to-live in seconds"
    },
    "performance.max_search_results": {
        "value": 100,
        "category": "performance",
        "description": "Maximum search results to return"
    },
    "performance.database_query_timeout": {
        "value": 30,
        "category": "performance",
        "description": "Database query timeout in seconds"
    }
}


class SystemConfigService:
    """
    Service class for system configuration business logic.

    This class handles all configuration management operations, including
    defaults, validation, schema generation, and business rules.

    Responsibilities:
    - Initialize default configurations
    - Validate configuration values
    - Provide configuration schema
    - Handle bulk operations
    - Manage configuration exports
    """

    def __init__(self, db: Session):
        """
        Initialize the SystemConfigService.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.repository = SystemConfigRepository(db)

    def initialize_default_configurations(self) -> Dict[str, Any]:
        """
        Initialize all default configurations in the database.
        Creates or updates configurations to match DEFAULT_CONFIGURATIONS.

        Returns:
            Dict[str, Any]: Result with created and updated counts
        """
        created_count = 0
        updated_count = 0

        for key, config_data in DEFAULT_CONFIGURATIONS.items():
            existing = self.repository.get_by_key(key)

            if existing:
                # Update if inactive or description changed
                if not existing.is_active or existing.description != config_data["description"]:
                    existing.is_active = True
                    existing.description = config_data["description"]
                    self.repository.update(existing)
                    updated_count += 1
            else:
                # Create new configuration
                new_config = SystemConfiguration(
                    key=key,
                    value=config_data["value"],
                    category=config_data["category"],
                    description=config_data["description"]
                )
                self.repository.create(new_config)
                created_count += 1

        return {
            "created": created_count,
            "updated": updated_count,
            "total": len(DEFAULT_CONFIGURATIONS)
        }

    def get_configuration_value(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get configuration value by key with fallback to default.

        Args:
            key (str): Configuration key
            default (Any): Default value if not found

        Returns:
            Any: Configuration value or default
        """
        config = self.repository.get_active_by_key(key)

        if config:
            return config.value

        # Try to get from DEFAULT_CONFIGURATIONS
        if key in DEFAULT_CONFIGURATIONS:
            return DEFAULT_CONFIGURATIONS[key]["value"]

        return default

    def validate_configuration(
        self,
        key: str,
        value: Any
    ) -> tuple[bool, List[str]]:
        """
        Validate a configuration value.

        Args:
            key (str): Configuration key
            value (Any): Value to validate

        Returns:
            tuple[bool, List[str]]: (is_valid, list of errors)
        """
        errors = []

        # Email validation - only for actual email address fields
        email_fields = ["company_email"]
        for email_field in email_fields:
            if email_field in key:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    errors.append(f"Invalid email format for {key}")

        # Integer validation for specific keys
        integer_keys = [
            "min_password_length",
            "session_timeout_minutes",
            "max_login_attempts",
            "lockout_duration_minutes",
            "audit_log_retention_days",
            "backup_retention_days",
            "api_rate_limit",
            "cache_ttl_seconds",
            "max_search_results",
            "database_query_timeout",
            "deal_inactivity_warning_days",
            "opportunity_auto_close_days"
        ]

        for int_key in integer_keys:
            if int_key in key:
                try:
                    int_value = int(value)
                    if int_value < 0:
                        errors.append(f"{key} must be a positive integer")
                except (ValueError, TypeError):
                    errors.append(f"{key} must be an integer")

        # Boolean validation for specific keys
        boolean_keys = [
            "email_notifications",
            "deal_update_notifications",
            "task_reminders",
            "weekly_reports",
            "system_alerts",
            "two_factor_auth",
            "data_encryption_at_rest",
            "enable_automatic_backups",
            "compress_backups",
            "crm_sync_enabled",
            "enable_caching",
            "require_deal_value",
            "auto_progress_deals",
            "lead_scoring_enabled",
            "lead_assignment_alerts",
            "quota_achievement_alerts"
        ]

        for bool_key in boolean_keys:
            if bool_key in key:
                if not isinstance(value, bool):
                    errors.append(f"{key} must be a boolean")

        return len(errors) == 0, errors

    def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get the configuration schema with categories and field types.

        Returns:
            Dict[str, Any]: Schema definition
        """
        categories = {
            "general": {
                "label": "General Settings",
                "description": "Basic system configuration",
                "icon": "settings",
                "order": 1
            },
            "sales": {
                "label": "Sales Settings",
                "description": "Sales pipeline and deal configuration",
                "icon": "trending-up",
                "order": 2
            },
            "notifications": {
                "label": "Notification Settings",
                "description": "Email and alert configuration",
                "icon": "bell",
                "order": 3
            },
            "security": {
                "label": "Security Settings",
                "description": "Authentication and security configuration",
                "icon": "shield",
                "order": 4
            },
            "backup": {
                "label": "Backup Settings",
                "description": "Data backup configuration",
                "icon": "database",
                "order": 5
            },
            "integrations": {
                "label": "Integration Settings",
                "description": "Third-party service integrations",
                "icon": "link",
                "order": 6
            },
            "performance": {
                "label": "Performance Settings",
                "description": "System performance and optimization",
                "icon": "zap",
                "order": 7
            }
        }

        field_types = {
            "company_email": {"type": "email"},
            "time_format": {"type": "select", "options": ["12h", "24h"]},
            "password_complexity": {"type": "select", "options": ["low", "medium", "high"]},
            "backup_frequency": {"type": "select", "options": ["hourly", "daily", "weekly"]},
            "email_service_provider": {"type": "select", "options": ["smtp", "sendgrid", "mailgun"]},
            "calendar_integration": {"type": "select", "options": ["none", "google", "outlook"]},
            "default_pipeline_stage": {"type": "select", "options": ["new", "contacted", "qualified", "proposal", "negotiation", "closed"]},
        }

        return {
            "categories": categories,
            "field_types": field_types
        }

    def bulk_update_configurations(
        self,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update multiple configurations with validation.

        Args:
            updates (List[Dict[str, Any]]): List of configuration updates

        Returns:
            Dict[str, Any]: Result with success/error counts
        """
        validated_updates = []
        validation_errors = []

        # Validate all updates first
        for update in updates:
            key = update.get("key")
            value = update.get("value")

            if not key:
                validation_errors.append("Missing configuration key")
                continue

            is_valid, errors = self.validate_configuration(key, value)
            if not is_valid:
                validation_errors.extend(errors)
            else:
                validated_updates.append(update)

        # If there are validation errors, return them
        if validation_errors:
            return {
                "success": False,
                "updated": 0,
                "errors": validation_errors
            }

        # Perform bulk update
        updated_count, update_errors = self.repository.bulk_update(
            validated_updates)

        return {
            "success": len(update_errors) == 0,
            "updated": updated_count,
            "errors": update_errors
        }

    def export_configurations(self) -> Dict[str, Any]:
        """
        Export all configurations with metadata.

        Returns:
            Dict[str, Any]: Export data
        """
        export_data = self.repository.get_export_data()

        return {
            "export_date": datetime.utcnow().isoformat(),
            "configurations": export_data,
            "metadata": {
                "total_count": len(export_data),
                "categories": self.repository.get_categories(),
                "version": "1.0"
            }
        }

    def validate_bulk_configurations(
        self,
        configurations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate multiple configurations without saving.

        Args:
            configurations (List[Dict[str, Any]]): Configurations to validate

        Returns:
            Dict[str, Any]: Validation results
        """
        errors = []
        warnings = []
        valid_count = 0

        for config in configurations:
            key = config.get("key")
            value = config.get("value")

            if not key:
                errors.append("Configuration missing key")
                continue

            is_valid, config_errors = self.validate_configuration(key, value)

            if is_valid:
                valid_count += 1
            else:
                errors.extend(config_errors)

            # Check if configuration exists
            existing = self.repository.get_by_key(key)
            if not existing:
                warnings.append(
                    f"Configuration {key} does not exist and will be created")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "valid_count": valid_count,
            "total_count": len(configurations)
        }

    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current effective configuration (all active configs as dict).

        Returns:
            Dict[str, Any]: Current configuration values
        """
        return self.repository.get_as_dict(nested=True)

    def get_configurations_by_category(
        self,
        categories: Optional[List[str]] = None
    ) -> Dict[str, List[SystemConfiguration]]:
        """
        Get configurations organized by categories with metadata.

        Args:
            categories (Optional[List[str]]): Specific categories to retrieve

        Returns:
            Dict[str, List[SystemConfiguration]]: Configurations by category
        """
        if categories:
            result = {}
            for category in categories:
                result[category] = self.repository.get_by_category(category)
            return result
        else:
            return self.repository.get_grouped_by_category()
