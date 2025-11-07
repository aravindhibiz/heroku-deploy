"""
Database initialization script for roles, permissions, and system configuration
Run this after creating tables to populate initial data
"""
from sqlalchemy.orm import Session
from app.core.database import get_db, engine
from app.models.role import Role, Permission
from app.models.system_config import SystemConfiguration


def init_permissions(db: Session):
    """Initialize default permissions"""
    permissions_data = [
        # Dashboard & Analytics
        {"name": "view_dashboard", "display_name": "View Dashboard",
            "category": "Dashboard & Analytics"},
        {"name": "view_analytics", "display_name": "View Analytics",
            "category": "Dashboard & Analytics"},
        {"name": "export_reports", "display_name": "Export Reports",
            "category": "Dashboard & Analytics"},

        # Contact Management
        {"name": "view_contacts", "display_name": "View Contacts",
            "category": "Contact Management"},
        {"name": "create_contacts", "display_name": "Create Contacts",
            "category": "Contact Management"},
        {"name": "edit_contacts", "display_name": "Edit Contacts",
            "category": "Contact Management"},
        {"name": "delete_contacts", "display_name": "Delete Contacts",
            "category": "Contact Management"},
        {"name": "import_export_contacts", "display_name": "Import/Export Contacts",
            "category": "Contact Management"},

        # Deal Management
        {"name": "view_deals", "display_name": "View Deals",
            "category": "Deal Management"},
        {"name": "create_deals", "display_name": "Create Deals",
            "category": "Deal Management"},
        {"name": "edit_deals", "display_name": "Edit Deals",
            "category": "Deal Management"},
        {"name": "delete_deals", "display_name": "Delete Deals",
            "category": "Deal Management"},
        {"name": "move_pipeline_stages", "display_name": "Move Pipeline Stages",
            "category": "Deal Management"},

        # User Management
        {"name": "view_users", "display_name": "View Users",
            "category": "User Management"},
        {"name": "invite_users", "display_name": "Invite Users",
            "category": "User Management"},
        {"name": "edit_user_roles", "display_name": "Edit User Roles",
            "category": "User Management"},
        {"name": "deactivate_users", "display_name": "Deactivate Users",
            "category": "User Management"},

        # System Configuration
        {"name": "manage_integrations", "display_name": "Manage Integrations",
            "category": "System Configuration"},
        {"name": "configure_custom_fields", "display_name": "Configure Custom Fields",
            "category": "System Configuration"},
        {"name": "manage_email_templates", "display_name": "Manage Email Templates",
            "category": "System Configuration"},
        {"name": "access_system_settings", "display_name": "Access System Settings",
            "category": "System Configuration"},
    ]

    for perm_data in permissions_data:
        existing = db.query(Permission).filter(
            Permission.name == perm_data["name"]).first()
        if not existing:
            permission = Permission(**perm_data)
            db.add(permission)

    db.commit()


def init_roles(db: Session):
    """Initialize default roles with permissions"""
    # Get all permissions
    permissions = {p.name: p for p in db.query(Permission).all()}

    # Define roles and their permissions
    roles_data = [
        {
            "name": "admin",
            "display_name": "Admin",
            "description": "Full system access",
            "permissions": list(permissions.keys())  # All permissions
        },
        {
            "name": "sales_manager",
            "display_name": "Sales Manager",
            "description": "Team management access",
            "permissions": [
                "view_dashboard", "view_analytics", "export_reports",
                "view_contacts", "create_contacts", "edit_contacts", "import_export_contacts",
                "view_deals", "create_deals", "edit_deals", "move_pipeline_stages",
                "view_users", "manage_email_templates"
            ]
        },
        {
            "name": "sales_rep",
            "display_name": "Sales Rep",
            "description": "Standard user access",
            "permissions": [
                "view_dashboard",
                "view_contacts", "create_contacts", "edit_contacts",
                "view_deals", "create_deals", "edit_deals", "move_pipeline_stages"
            ]
        },
        {
            "name": "sales_operations",
            "display_name": "Sales Operations",
            "description": "Operations and configuration access",
            "permissions": [
                "view_dashboard", "view_analytics", "export_reports",
                "view_contacts", "create_contacts", "edit_contacts", "delete_contacts", "import_export_contacts",
                "view_deals",
                "view_users",
                "manage_integrations", "configure_custom_fields", "manage_email_templates", "access_system_settings"
            ]
        }
    ]

    for role_data in roles_data:
        existing = db.query(Role).filter(
            Role.name == role_data["name"]).first()
        if not existing:
            role = Role(
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"]
            )

            # Add permissions
            for perm_name in role_data["permissions"]:
                if perm_name in permissions:
                    role.permissions.append(permissions[perm_name])

            db.add(role)

    db.commit()


def init_system_config(db: Session):
    """Initialize default system configuration"""
    configs = [
        # General settings
        {"key": "company_name", "value": "SalesFlow Pro Inc.", "category": "general"},
        {"key": "timezone", "value": "America/New_York", "category": "general"},
        {"key": "date_format", "value": "MM/DD/YYYY", "category": "general"},
        {"key": "currency", "value": "USD", "category": "general"},
        {"key": "language", "value": "en", "category": "general"},

        # Sales settings
        {"key": "default_pipeline_stage", "value": "Prospecting", "category": "sales"},
        {"key": "deal_currency", "value": "USD", "category": "sales"},
        {"key": "require_deal_value", "value": True, "category": "sales"},
        {"key": "auto_progress_deals", "value": False, "category": "sales"},
        {"key": "deal_inactivity_days", "value": 30, "category": "sales"},

        # Notification settings
        {"key": "email_notifications", "value": True, "category": "notifications"},
        {"key": "deal_update_notifications",
            "value": True, "category": "notifications"},
        {"key": "task_reminders", "value": True, "category": "notifications"},
        {"key": "weekly_reports", "value": True, "category": "notifications"},
        {"key": "system_alerts", "value": True, "category": "notifications"},

        # Security settings
        {"key": "password_complexity", "value": True, "category": "security"},
        {"key": "two_factor_auth", "value": False, "category": "security"},
        {"key": "session_timeout", "value": 480, "category": "security"},
        {"key": "login_attempts", "value": 5, "category": "security"},
        {"key": "data_encryption", "value": True, "category": "security"},

        # Backup settings
        {"key": "auto_backup", "value": True, "category": "backup"},
        {"key": "backup_frequency", "value": "daily", "category": "backup"},
        {"key": "retention_days", "value": 30, "category": "backup"},
        {"key": "backup_location", "value": "cloud", "category": "backup"},
    ]

    for config_data in configs:
        existing = db.query(SystemConfiguration).filter(
            SystemConfiguration.key == config_data["key"]
        ).first()
        if not existing:
            config = SystemConfiguration(**config_data)
            db.add(config)

    db.commit()


def main():
    """Initialize database with default data"""
    db = next(get_db())

    print("Initializing permissions...")
    init_permissions(db)

    print("Initializing roles...")
    init_roles(db)

    print("Initializing system configuration...")
    init_system_config(db)

    print("Database initialization complete!")
    db.close()


if __name__ == "__main__":
    main()
