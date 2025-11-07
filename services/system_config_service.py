"""
System Configuration Management Service
This service handles default configurations and initialization
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ..models.system_config import SystemConfiguration
from ..core.database import SessionLocal


class SystemConfigManager:
    """Service for managing system configurations"""

    DEFAULT_CONFIGURATIONS = {
        # General Settings
        "general.company_name": {
            "value": "SalesFlow Pro Inc.",
            "category": "general",
            "description": "Company name displayed throughout the application"
        },
        "general.company_email": {
            "value": "admin@salesflowpro.com",
            "category": "general",
            "description": "Primary company email address"
        },
        "general.company_phone": {
            "value": "+1-555-123-4567",
            "category": "general",
            "description": "Primary company phone number"
        },
        "general.company_address": {
            "value": "123 Business Street, Suite 100, Business City, BC 12345",
            "category": "general",
            "description": "Company physical address"
        },
        "general.timezone": {
            "value": "America/New_York",
            "category": "general",
            "description": "Default timezone for the application"
        },
        "general.date_format": {
            "value": "MM/DD/YYYY",
            "category": "general",
            "description": "Date format used throughout the application"
        },
        "general.time_format": {
            "value": "12",
            "category": "general",
            "description": "Time format (12 or 24 hour)"
        },
        "general.currency": {
            "value": "USD",
            "category": "general",
            "description": "Default currency for deals and financial data"
        },
        "general.language": {
            "value": "en",
            "category": "general",
            "description": "Default application language"
        },

        # Sales Settings
        "sales.default_pipeline_stage": {
            "value": "prospecting",
            "category": "sales",
            "description": "Default stage for new deals"
        },
        "sales.deal_currency": {
            "value": "USD",
            "category": "sales",
            "description": "Default currency for new deals"
        },
        "sales.require_deal_value": {
            "value": True,
            "category": "sales",
            "description": "Require deal value to be set"
        },
        "sales.auto_progress_deals": {
            "value": False,
            "category": "sales",
            "description": "Automatically progress deals based on activities"
        },
        "sales.deal_inactivity_warning_days": {
            "value": 30,
            "category": "sales",
            "description": "Days before warning about inactive deals"
        },
        "sales.lead_scoring_enabled": {
            "value": True,
            "category": "sales",
            "description": "Enable automatic lead scoring"
        },
        "sales.opportunity_auto_close_days": {
            "value": 90,
            "category": "sales",
            "description": "Auto-close opportunities after X days of inactivity"
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
            "description": "Send notifications on deal updates"
        },
        "notifications.task_reminders": {
            "value": True,
            "category": "notifications",
            "description": "Send task reminder notifications"
        },
        "notifications.weekly_reports": {
            "value": True,
            "category": "notifications",
            "description": "Send weekly performance reports"
        },
        "notifications.system_alerts": {
            "value": True,
            "category": "notifications",
            "description": "Send system maintenance alerts"
        },
        "notifications.lead_assignment_alerts": {
            "value": True,
            "category": "notifications",
            "description": "Send alerts when leads are assigned"
        },
        "notifications.quota_achievement_alerts": {
            "value": True,
            "category": "notifications",
            "description": "Send alerts when quotas are achieved"
        },

        # Security Settings
        "security.password_complexity": {
            "value": True,
            "category": "security",
            "description": "Enforce complex password requirements"
        },
        "security.min_password_length": {
            "value": 8,
            "category": "security",
            "description": "Minimum password length"
        },
        "security.two_factor_auth": {
            "value": False,
            "category": "security",
            "description": "Enable two-factor authentication"
        },
        "security.session_timeout_minutes": {
            "value": 480,
            "category": "security",
            "description": "Session timeout in minutes (8 hours default)"
        },
        "security.max_login_attempts": {
            "value": 5,
            "category": "security",
            "description": "Maximum login attempts before lockout"
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
            "value": 365,
            "category": "security",
            "description": "Number of days to retain audit logs"
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
            "description": "Backup frequency (daily, weekly, monthly)"
        },
        "backup.backup_retention_days": {
            "value": 30,
            "category": "backup",
            "description": "Number of days to retain backups"
        },
        "backup.backup_location": {
            "value": "local",
            "category": "backup",
            "description": "Backup storage location (local, s3, azure)"
        },
        "backup.compress_backups": {
            "value": True,
            "category": "backup",
            "description": "Compress backup files"
        },

        # Integration Settings
        "integrations.email_service_provider": {
            "value": "sendgrid",
            "category": "integrations",
            "description": "Email service provider (sendgrid, mailgun, ses)"
        },
        "integrations.calendar_integration": {
            "value": "google",
            "category": "integrations",
            "description": "Calendar integration service"
        },
        "integrations.crm_sync_enabled": {
            "value": False,
            "category": "integrations",
            "description": "Enable external CRM synchronization"
        },
        "integrations.api_rate_limit": {
            "value": 1000,
            "category": "integrations",
            "description": "API requests per hour limit"
        },

        # Performance Settings
        "performance.enable_caching": {
            "value": True,
            "category": "performance",
            "description": "Enable application caching"
        },
        "performance.cache_ttl_seconds": {
            "value": 3600,
            "category": "performance",
            "description": "Cache time-to-live in seconds"
        },
        "performance.max_search_results": {
            "value": 100,
            "category": "performance",
            "description": "Maximum search results per query"
        },
        "performance.database_query_timeout": {
            "value": 30,
            "category": "performance",
            "description": "Database query timeout in seconds"
        }
    }

    @classmethod
    def initialize_default_configurations(cls, db: Session = None) -> bool:
        """Initialize system with default configurations"""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False

        try:
            created_count = 0
            updated_count = 0

            for key, config_data in cls.DEFAULT_CONFIGURATIONS.items():
                # Check if configuration already exists
                existing_config = db.query(SystemConfiguration).filter(
                    SystemConfiguration.key == key
                ).first()

                if existing_config:
                    # Update description if changed
                    if existing_config.description != config_data["description"]:
                        existing_config.description = config_data["description"]
                        updated_count += 1
                else:
                    # Create new configuration
                    new_config = SystemConfiguration(
                        key=key,
                        value=config_data["value"],
                        category=config_data["category"],
                        description=config_data["description"]
                    )
                    db.add(new_config)
                    created_count += 1

            db.commit()
            print(
                f"✅ System configuration initialized: {created_count} created, {updated_count} updated")
            return True

        except Exception as e:
            print(f"❌ Error initializing system configuration: {e}")
            db.rollback()
            return False
        finally:
            if close_db:
                db.close()

    @classmethod
    def get_configuration_value(cls, key: str, db: Session = None) -> Any:
        """Get a configuration value by key"""
        if db is None:
            from ..core.database import get_db
            db = next(get_db())
            close_db = True
        else:
            close_db = False

        try:
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == key,
                SystemConfiguration.is_active == True
            ).first()

            if config:
                return config.value

            # Fallback to default value
            if key in cls.DEFAULT_CONFIGURATIONS:
                return cls.DEFAULT_CONFIGURATIONS[key]["value"]

            return None

        except Exception as e:
            print(f"Error getting configuration {key}: {e}")
            return None
        finally:
            if close_db:
                db.close()

    @classmethod
    def get_configuration_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for validation"""
        return {
            "categories": {
                "general": {
                    "label": "General Settings",
                    "description": "Basic company and system settings",
                    "icon": "Settings"
                },
                "sales": {
                    "label": "Sales Settings",
                    "description": "Sales process and pipeline configuration",
                    "icon": "Target"
                },
                "notifications": {
                    "label": "Notifications",
                    "description": "Email and alert notification settings",
                    "icon": "Bell"
                },
                "security": {
                    "label": "Security",
                    "description": "Security and access control settings",
                    "icon": "Shield"
                },
                "backup": {
                    "label": "Backup & Recovery",
                    "description": "Data backup and recovery settings",
                    "icon": "Database"
                },
                "integrations": {
                    "label": "Integrations",
                    "description": "Third-party service integrations",
                    "icon": "Link"
                },
                "performance": {
                    "label": "Performance",
                    "description": "System performance and optimization",
                    "icon": "Zap"
                }
            },
            "field_types": {
                "string": ["company_name", "company_email", "timezone", "currency", "language"],
                "boolean": ["require_deal_value", "auto_progress_deals", "email_notifications"],
                "integer": ["deal_inactivity_warning_days", "session_timeout_minutes", "max_login_attempts"],
                "select": {
                    "backup_frequency": ["daily", "weekly", "monthly"],
                    "date_format": ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"],
                    "time_format": ["12", "24"],
                    "email_service_provider": ["sendgrid", "mailgun", "ses"],
                    "backup_location": ["local", "s3", "azure"]
                }
            }
        }

    @classmethod
    def validate_configuration(cls, key: str, value: Any) -> bool:
        """Validate a configuration value"""
        if key not in cls.DEFAULT_CONFIGURATIONS:
            return False

        # Add specific validation rules here
        if key.endswith("_days") or key.endswith("_minutes") or key.endswith("_seconds"):
            return isinstance(value, int) and value > 0

        if key.endswith("_enabled") or key.startswith("enable_"):
            return isinstance(value, bool)

        # Only validate email format for keys that are actually email addresses
        if (key.endswith("_email") or key.endswith(".email")) and isinstance(value, str):
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(email_pattern, value) is not None

        return True
