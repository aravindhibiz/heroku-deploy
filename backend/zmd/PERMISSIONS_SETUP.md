# Dynamic Role-Based Permission System Setup

## Overview

This CRM application now supports a fully dynamic role-based permission system where permissions can be managed from the frontend Settings → Permissions page.

## Initial Setup

### 1. Seed the Database with Permissions

Run the permission seeder script to populate the database with all application permissions and assign default permissions to roles:

```bash
cd backend
python seed_permissions.py
```

This will:
- Create all permission records in the `permissions` table
- Create or update role records (admin, sales_manager, sales_rep, user)
- Assign default permissions to each role

### 2. Default Permission Assignments

#### Admin Role
Gets ALL permissions including:
- All dashboard and analytics permissions
- All deal, contact, and activity permissions (view, create, edit, delete)
- All settings and configuration permissions

#### Sales Manager Role
Gets most permissions except:
- System configuration
- Permission management
Has:
- View/edit all deals and contacts
- Team analytics
- User management
- Integrations, custom fields, email templates

#### Sales Rep Role
Gets permissions for own data:
- View/edit own deals and contacts
- Create deals and contacts
- Personal analytics
- Email templates

#### User Role
Gets minimal view-only permissions:
- View own deals and contacts
- View dashboard
- View own profile

## Permission Structure

Permissions follow the format: `category.action`

Examples:
- `deals.view_all` - View all deals
- `deals.view_own` - View only own deals
- `contacts.create` - Create contacts
- `settings.user_management` - Manage users
- `analytics.view_team` - View team analytics

## How to Use

### Backend - Protecting Routes

```python
from app.core.auth import require_permission, require_any_permission

# Require a specific permission
@router.get("/")
async def get_all_deals(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_permission("deals.view_all"))
):
    # Only users with deals.view_all permission can access this
    pass

# Require any one of multiple permissions
@router.get("/")
async def get_deals(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(
        require_any_permission(["deals.view_all", "deals.view_own"])
    )
):
    # User needs either permission
    pass
```

### Backend - Checking Permissions in Code

```python
from app.core.auth import has_permission
from app.core.auth_helpers import get_deals_query_filter

# Check if user has a permission
if has_permission(db, current_user, "deals.edit_all"):
    # Can edit all deals
    pass

# Use helper functions for data filtering
query = get_deals_query_filter(db, current_user, base_query)
```

### Frontend - Route Protection

```jsx
import ProtectedRoute from '../components/ProtectedRoute';

// Require a single permission
<ProtectedRoute requiredPermission="deals.view_all">
  <DealsPage />
</ProtectedRoute>

// Require any one of multiple permissions
<ProtectedRoute requiredPermissions={["deals.view_all", "deals.view_own"]}>
  <DealsPage />
</ProtectedRoute>
```

### Frontend - Conditional Rendering

```jsx
import { useAuth } from '../contexts/AuthContext';
import RoleBasedNavigation from '../components/RoleBasedNavigation';

function MyComponent() {
  const { hasPermission, hasAnyPermission } = useAuth();

  return (
    <div>
      {/* Show element only if user has permission */}
      {hasPermission('contacts.create') && (
        <button>Create Contact</button>
      )}- 10.2. 

      {/* Using RoleBasedNavigation component */}
      <RoleBasedNavigation requiredPermission="deals.edit_all">
        <button>Edit Deal</button>
      </RoleBasedNavigation>
    </div>
  );
}
```

## Managing Permissions from Frontend

1. Login as an admin user
2. Navigate to Settings → Permissions
3. Select a role from the left sidebar
4. Check/uncheck permissions for that role
5. Click "Save Changes"

All users with that role will immediately get the updated permissions (they may need to refresh their browser).

## Available Permission Categories

1. **Dashboard & Analytics**
   - View stats, filter data, pipeline operations, analytics

2. **Deals**
   - View all/own, create, edit all/own, delete all/own, move stages

3. **Contacts**
   - View all/own, create, edit all/own, delete all/own, import, export

4. **Activities**
   - View all/own, create all/own, edit all/own, delete all/own, export

5. **Settings**
   - User management, permissions, integrations, custom fields, email templates, system config, profile

## Adding New Permissions

1. Add the permission to `backend/app/seeds/permissions_seed.py` in the `get_all_permissions()` function
2. Run `python seed_permissions.py` to add it to the database
3. Assign it to roles in `get_default_role_permissions()` or via the frontend UI
4. Use it in your route protection or UI logic

## Troubleshooting

### Permissions not loading
- Check browser console for errors
- Verify backend is running and accessible
- Check that `/api/v1/auth/me/permissions` endpoint returns data

### Permission changes not taking effect
- Clear localStorage: `localStorage.clear()`
- Refresh the page
- Re-login

### Seeder fails
- Check database connection
- Verify migrations are up to date
- Check for duplicate permission names
