# Activity Module - New Architecture Testing Guide

## 🧪 Testing the New Implementation

### Prerequisites
Before testing, ensure:
1. Database is running
2. All dependencies are installed
3. Backend server can start

### Step 1: Switch to New Routes (Temporary - For Testing)

You have two options:

#### Option A: Test Alongside Old Routes
Add the new routes with a different prefix to test without affecting existing functionality:

**In `app/main.py`**, add after the existing activities route:
```python
from .routes import activities_new

# Add this line after the existing activities router
app.include_router(
    activities_new.router,
    prefix="/api/v1/activities-v2",  # Different prefix for testing
    tags=["activities-v2"]
)
```

This allows you to test the new implementation at `/api/v1/activities-v2` while the old `/api/v1/activities` still works.

#### Option B: Replace Old Routes Completely
**In `app/main.py`**, replace the old activities import and router:

Change:
```python
from .routes import auth, contacts, deals, companies, activities, tasks, ...
```

To:
```python
from .routes import auth, contacts, deals, companies, activities_new as activities, tasks, ...
```

The router registration stays the same. The new routes will now serve `/api/v1/activities`.

---

## 🔧 Manual Testing Checklist

### 1. Test GET /api/v1/activities (or activities-v2)
```bash
# Using curl (PowerShell)
$headers = @{
    "Authorization" = "Bearer YOUR_ACCESS_TOKEN"
}
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/activities" -Headers $headers

# Expected: List of activities based on user permissions
```

### 2. Test GET /api/v1/activities/{id}
```bash
$headers = @{
    "Authorization" = "Bearer YOUR_ACCESS_TOKEN"
}
$activityId = "YOUR_ACTIVITY_UUID"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/activities/$activityId" -Headers $headers

# Expected: Single activity with relations and custom fields
```

### 3. Test POST /api/v1/activities
```bash
$headers = @{
    "Authorization" = "Bearer YOUR_ACCESS_TOKEN"
    "Content-Type" = "application/json"
}
$body = @{
    type = "meeting"
    subject = "Test Meeting"
    description = "Testing new architecture"
    duration_minutes = 60
    contact_id = "CONTACT_UUID_HERE"  # Optional
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/activities" -Headers $headers -Body $body

# Expected: Created activity with 201 status
```

### 4. Test PUT /api/v1/activities/{id}
```bash
$headers = @{
    "Authorization" = "Bearer YOUR_ACCESS_TOKEN"
    "Content-Type" = "application/json"
}
$activityId = "YOUR_ACTIVITY_UUID"
$body = @{
    subject = "Updated Meeting Title"
    duration_minutes = 90
} | ConvertTo-Json

Invoke-RestMethod -Method Put -Uri "http://localhost:8000/api/v1/activities/$activityId" -Headers $headers -Body $body

# Expected: Updated activity
```

### 5. Test DELETE /api/v1/activities/{id}
```bash
$headers = @{
    "Authorization" = "Bearer YOUR_ACCESS_TOKEN"
}
$activityId = "YOUR_ACTIVITY_UUID"
Invoke-RestMethod -Method Delete -Uri "http://localhost:8000/api/v1/activities/$activityId" -Headers $headers

# Expected: Success message
```

---

## 🎯 What to Verify

### Functionality Parity
Ensure the new implementation has **100% feature parity** with the old:

- [x] **GET all activities** - Returns activities based on permissions (view_all vs view_own)
- [x] **GET single activity** - Returns activity with relations (contact, deal, user)
- [x] **POST create activity** - Creates with custom fields support
- [x] **PUT update activity** - Updates with custom fields support
- [x] **DELETE activity** - Deletes with permission checks

### Permission Checks
Test with different user roles:

1. **Admin user** (activities.view_all, activities.create_all, activities.edit_all, activities.delete_all)
   - Should see all activities
   - Should be able to create/edit/delete any activity

2. **Regular user** (activities.view_own, activities.create_own, activities.edit_own, activities.delete_own)
   - Should see only their own activities
   - Should be able to create activities
   - Should be able to edit/delete only their own activities

3. **Unauthorized user** (no permissions)
   - Should get 403 Forbidden errors

### Custom Fields
Test custom field functionality:

1. Create activity with custom fields
2. Update activity custom fields
3. Retrieve activity with custom fields
4. Verify custom fields persist correctly

---

## 🐛 Common Issues & Solutions

### Issue 1: Import Errors
**Symptom**: `ImportError` or `ModuleNotFoundError`

**Solution**:
```bash
# Make sure you're in the backend directory
cd backend

# Restart the Python server
# The terminal should reload with the new code
```

### Issue 2: Database Connection Issues
**Symptom**: `Cannot connect to database`

**Solution**:
```bash
# Check if PostgreSQL is running
# Check .env file has correct DATABASE_URL
```

### Issue 3: 403 Forbidden on All Requests
**Symptom**: All requests return 403

**Solution**:
- Check JWT token is valid
- Verify user has appropriate permissions
- Check permission seeding script has run

### Issue 4: Custom Fields Not Saving
**Symptom**: Custom fields return null

**Solution**:
- Verify custom field definitions exist in database
- Check CustomFieldService is working
- Ensure EntityType.ACTIVITY is correct

---

## 📊 Performance Comparison

Compare the new vs old implementation:

### Database Queries
```python
# OLD: Multiple queries scattered in route
# - Query for activity
# - Query for custom fields
# - Query for permissions
# - etc.

# NEW: Optimized queries in repository
# - Single query with joinedload for relations
# - Batch operations where possible
```

### Response Time
Test and compare:
```bash
# Measure response time for GET /api/v1/activities
# Old route vs new route
# Should be similar or better
```

---

## ✅ Success Criteria

The migration is successful when:

1. ✅ All endpoints return correct responses
2. ✅ Permission checks work correctly
3. ✅ Custom fields are saved and retrieved
4. ✅ No errors in server logs
5. ✅ Response times are acceptable
6. ✅ Frontend integration works without changes
7. ✅ All edge cases handled (not found, forbidden, etc.)

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All tests pass
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Migration plan documented
- [ ] Rollback plan ready
- [ ] Monitoring in place
- [ ] Performance tested
- [ ] Security reviewed

---

## 📝 Rollback Plan

If issues arise in production:

1. **Immediate rollback**: 
   - Change import in `main.py` back to old `activities` route
   - Restart server
   - Old functionality restored

2. **Files to keep**:
   - Keep `routes/activities.py` (old) until new is proven stable
   - Don't delete until 100% confident

3. **Monitoring**:
   - Watch error logs
   - Monitor response times
   - Check user reports

---

## 🎓 Learning Points

After testing, you should understand:

1. **How layers interact**: Route → Controller → Service → Repository
2. **Why separation matters**: Each layer can be tested independently
3. **Reusability**: Service and repository can be used by other features
4. **Maintainability**: Changes are isolated to specific layers

---

## 📞 Support

If you encounter issues:

1. Check the logs in terminal
2. Review the ARCHITECTURE.md
3. Compare with ACTIVITY_MIGRATION.md
4. Test each layer independently

---

**Good luck with testing! 🚀**

Once Activity module is proven stable, we'll migrate the remaining modules using this as a template.
