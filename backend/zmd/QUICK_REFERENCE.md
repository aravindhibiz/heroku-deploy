# Quick Reference - New Backend Architecture

## 📋 Layer Responsibilities (One-Liner Each)

| Layer | File | Responsibility | Key Rule |
|-------|------|----------------|----------|
| **Model** | `models/activity.py` | Database table structure | Just SQLAlchemy definitions |
| **Schema** | `schemas/activity.py` | Request/response validation | Just Pydantic models |
| **Repository** | `repositories/activity_repository.py` | Database queries | Pure data access, no business logic |
| **Service** | `services/activity_service.py` | Business logic & orchestration | No HTTP, no direct DB queries |
| **Controller** | `controllers/activity_controller.py` | HTTP handling & permissions | No business logic, no queries |
| **Route** | `routes/activities_new.py` | API endpoints | Just route definitions |

---

## 🔄 Request Flow (Simple)

```
HTTP Request
    ↓
Route (instantiate controller)
    ↓
Controller (check permissions, call service)
    ↓
Service (business logic, call repository)
    ↓
Repository (database query)
    ↓
Database
    ↓
Response flows back up
```

---

## 💻 Code Templates

### Creating a New Repository
```python
from .base_repository import BaseRepository
from ..models.your_model import YourModel

class YourRepository(BaseRepository[YourModel]):
    def __init__(self, db: Session):
        super().__init__(YourModel, db)
    
    def get_by_custom_field(self, field_value):
        return self.db.query(YourModel).filter(...).all()
```

### Creating a New Service
```python
class YourService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = YourRepository(db)
    
    def create_item(self, data: YourCreate, user: UserProfile):
        # Business logic
        item_dict = data.dict()
        item_dict['user_id'] = user.id
        
        # Use repository
        db_item = self.repository.create(obj_in=item_dict)
        self.db.commit()
        
        return self._build_response(db_item)
```

### Creating a New Controller
```python
class YourController:
    def __init__(self, db: Session):
        self.db = db
        self.service = YourService(db)
    
    async def create_item(self, data: YourCreate, user: UserProfile):
        # Check permissions
        if not self._check_permission(user):
            raise HTTPException(status_code=403)
        
        # Delegate to service
        try:
            return self.service.create_item(data, user)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
```

### Creating a New Route
```python
@router.post("/", response_model=YourResponse)
async def create_item(
    data: YourCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = YourController(db)
    return await controller.create_item(data, current_user)
```

---

## ✅ Do's and ❌ Don'ts

### Models
- ✅ DO: Define table structure, columns, relationships
- ❌ DON'T: Business logic, validation, queries

### Schemas
- ✅ DO: Pydantic models, validation rules
- ❌ DON'T: Database operations, business logic

### Repositories
- ✅ DO: All database queries, CRUD operations
- ❌ DON'T: Business logic, HTTP exceptions, permissions

### Services
- ✅ DO: Business logic, orchestration, transactions
- ❌ DON'T: HTTP handling, direct DB queries, permission checks

### Controllers
- ✅ DO: Permission checks, HTTP exceptions, call services
- ❌ DON'T: Business logic, database queries

### Routes
- ✅ DO: Define endpoints, dependency injection
- ❌ DON'T: Any logic beyond instantiating controllers

---

## 🎯 Quick Checklist for New Features

When adding a new feature:

1. **Model** - Create/update database model
2. **Schema** - Create request/response schemas
3. **Repository** - Create repository with query methods
4. **Service** - Create service with business logic
5. **Controller** - Create controller with HTTP handling
6. **Route** - Create route endpoints
7. **Test** - Test each layer independently

---

## 📂 File Organization

```
app/
├── models/
│   └── {entity}.py          # SQLAlchemy model
├── schemas/
│   └── {entity}.py          # Pydantic schemas
├── repositories/
│   ├── base_repository.py   # Base class (reusable)
│   └── {entity}_repository.py
├── services/
│   └── {entity}_service.py
├── controllers/
│   └── {entity}_controller.py
├── routes/
│   └── {entity}s.py         # Plural for REST convention
├── core/
│   ├── auth.py
│   ├── database.py
│   └── config.py
└── middleware/
    └── {middleware}.py
```

---

## 🔍 Debugging Guide

### Where to Look When:

**404 Not Found**
→ Check: Route definition → Controller get method → Service get method → Repository query

**403 Forbidden**
→ Check: Controller permission checks → User roles/permissions

**500 Internal Server Error**
→ Check: Service layer try/catch → Repository database operations

**Validation Error**
→ Check: Schema definitions

**Data Not Saving**
→ Check: Service commit() calls → Repository create/update methods

**Slow Performance**
→ Check: Repository queries (add indexes, use joinedload)

---

## 🧪 Testing Strategy

```python
# Test Repository (data access)
def test_repository():
    repo = ActivityRepository(test_db)
    activity = repo.create(obj_in={"type": "call", ...})
    assert activity.id is not None

# Test Service (business logic)
def test_service():
    service = ActivityService(test_db)
    activity = service.create_activity(create_data, user)
    assert activity.custom_fields is not None

# Test Controller (HTTP layer)
async def test_controller():
    controller = ActivityController(test_db)
    with pytest.raises(HTTPException):
        await controller.create_activity(data, unauthorized_user)

# Test Route (integration)
def test_route(client):
    response = client.post("/api/v1/activities", json={...})
    assert response.status_code == 201
```

---

## 📚 Key Files Reference

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | Complete architecture documentation |
| `ACTIVITY_MIGRATION.md` | Before/after comparison and migration guide |
| `TESTING_GUIDE.md` | How to test the new implementation |
| `QUICK_REFERENCE.md` | This file - quick lookup |

---

## 🚀 Migration Priority Order

1. ✅ **Activity** - DONE (reference implementation)
2. ⏳ **Contact** - Next (similar to Activity)
3. ⏳ **Company** - After Contact
4. ⏳ **Deal** - After Company
5. ⏳ **Task** - After Deal
6. ⏳ **Note** - After Task
7. ⏳ Rest of modules

---

## 💡 Pro Tips

1. **Always start with the repository** - Get data access right first
2. **Keep controllers thin** - Just permission checks and error handling
3. **Services own transactions** - commit/rollback in service layer
4. **Use type hints everywhere** - Makes debugging easier
5. **Write docstrings** - Future you will thank you
6. **Don't skip tests** - They save time in the long run
7. **Follow the Activity pattern** - It's the reference implementation

---

## 🎓 Remember

> "Clean code is not written by following a set of rules. You don't become a software craftsman by learning a list of what to do and what not to do. Professionalism and craftsmanship come from values that drive disciplines." - Robert C. Martin

**Your values**:
- Separation of concerns
- Single responsibility
- DRY (Don't Repeat Yourself)
- SOLID principles
- Clean, readable code

---

**Keep this file handy while working on the backend! 📌**
