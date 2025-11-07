# Backend Architecture - Production-Level Standard

## 📋 Overview

This document describes the standardized, production-level modular architecture for the CRM backend. The architecture follows industry best practices and implements clean separation of concerns with clear responsibilities for each layer.

## 🏗️ Architecture Layers

### 1. **Models** (`app/models/`)
**Purpose**: Database schema definitions

**Responsibilities**:
- Define SQLAlchemy ORM models
- Specify database table structures
- Define relationships between entities
- Set up indexes and constraints

**What it should NOT do**:
- Business logic
- Data validation (that's for schemas)
- Query logic (that's for repositories)

**Example**: `activity.py`
```python
class Activity(Base):
    __tablename__ = "activities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    # ... only structure definition
```

---

### 2. **Schemas** (`app/schemas/`)
**Purpose**: Request/response validation and serialization

**Responsibilities**:
- Define Pydantic models for API contracts
- Input validation
- Output serialization
- Type checking
- Documentation for API endpoints

**What it should NOT do**:
- Database operations
- Business logic
- Authentication/authorization

**Example**: `activity.py`
```python
class ActivityCreate(BaseModel):
    type: str
    subject: str
    # ... validation only
```

---

### 3. **Repositories** (`app/repositories/`) - **DATA ACCESS LAYER**
**Purpose**: Database operations and queries

**Responsibilities**:
- All database CRUD operations
- Complex queries
- Data retrieval logic
- Query optimization
- Transaction management at data level

**What it should NOT do**:
- Business logic
- Permission checks
- Response formatting
- HTTP-related operations

**Example**: `activity_repository.py`
```python
class ActivityRepository(BaseRepository[Activity]):
    def get_by_user(self, user_id: UUID) -> List[Activity]:
        return self.db.query(Activity).filter(...).all()
```

**Key Principles**:
- One repository per model/aggregate
- Returns database objects, not DTOs
- Encapsulates all SQL/ORM queries
- Reusable across multiple services

---

### 4. **Services** (`app/services/`) - **BUSINESS LOGIC LAYER**
**Purpose**: Business logic and orchestration

**Responsibilities**:
- Business rules and validations
- Orchestrating multiple repository calls
- Transaction management
- Coordinating with other services
- Data transformation
- Complex business operations

**What it should NOT do**:
- HTTP request/response handling
- Direct database queries (use repositories)
- Authentication (use middleware/controllers)

**Example**: `activity_service.py`
```python
class ActivityService:
    def create_activity(self, data: ActivityCreate, user: UserProfile):
        # Business logic
        activity_dict = data.dict(exclude={'custom_fields'})
        activity_dict['user_id'] = user.id
        
        # Use repository for data access
        db_activity = self.repository.create(obj_in=activity_dict)
        
        # Orchestrate with other services
        if custom_fields:
            CustomFieldService.save_custom_field_values(...)
        
        return self._build_response(db_activity)
```

**Key Principles**:
- One service per domain/aggregate
- Stateless (no instance variables except dependencies)
- Transaction boundaries defined here
- Returns DTOs/schemas, not raw database objects

---

### 5. **Controllers** (`app/controllers/`) - **HTTP LAYER**
**Purpose**: HTTP request/response handling

**Responsibilities**:
- Validate incoming requests
- Check permissions/authorization
- Call appropriate service methods
- Format responses
- HTTP status code handling
- Error handling and transformation

**What it should NOT do**:
- Business logic (delegate to services)
- Database operations (delegate to services)
- Complex data transformations

**Example**: `activity_controller.py`
```python
class ActivityController:
    async def create_activity(self, data: ActivityCreate, user: UserProfile):
        # Permission check
        if not self._check_create_permission(user):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Delegate to service
        try:
            return self.service.create_activity(data, user)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
```

**Key Principles**:
- Thin layer - just orchestration
- Handles HTTP concerns only
- Converts service exceptions to HTTP exceptions
- One controller per resource/domain

---

### 6. **Routes** (`app/routes/`) - **API ENDPOINTS**
**Purpose**: Define API endpoints and routing

**Responsibilities**:
- Define URL paths
- HTTP method mapping
- Dependency injection setup
- API documentation (OpenAPI)
- Request/response model binding

**What it should NOT do**:
- Business logic
- Permission checks (delegate to controllers)
- Data processing
- Database operations

**Example**: `activities_new.py`
```python
@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = ActivityController(db)
    return await controller.create_activity(activity_data, current_user)
```

**Key Principles**:
- Extremely thin - just route definitions
- No logic beyond instantiating controllers
- Clear, RESTful URL structure
- Comprehensive OpenAPI documentation

---

### 7. **Core** (`app/core/`)
**Purpose**: Core utilities and shared components

**Responsibilities**:
- Database configuration
- Authentication utilities
- Security functions
- Configuration management
- Shared helpers

---

### 8. **Middleware** (`app/middleware/`)
**Purpose**: Cross-cutting concerns

**Responsibilities**:
- Request/response logging
- Rate limiting
- CORS handling
- Error handling
- Request ID tracking
- Performance monitoring

---

## 🔄 Request Flow

```
1. HTTP Request
   ↓
2. Route (app/routes/)
   - Defines endpoint
   - Injects dependencies
   ↓
3. Controller (app/controllers/)
   - Validates request
   - Checks permissions
   - Handles HTTP concerns
   ↓
4. Service (app/services/)
   - Executes business logic
   - Orchestrates operations
   - Manages transactions
   ↓
5. Repository (app/repositories/)
   - Performs database queries
   - Returns database objects
   ↓
6. Database
   ↓
7. Response flows back up:
   Repository → Service → Controller → Route → HTTP Response
```

---

## 📁 Folder Structure

```
backend/
├── app/
│   ├── models/           # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── activity.py
│   │   └── ...
│   │
│   ├── schemas/          # Pydantic schemas (validation)
│   │   ├── __init__.py
│   │   ├── activity.py
│   │   └── ...
│   │
│   ├── repositories/     # Data access layer
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── activity_repository.py
│   │   └── ...
│   │
│   ├── services/         # Business logic layer
│   │   ├── __init__.py
│   │   ├── activity_service.py
│   │   └── ...
│   │
│   ├── controllers/      # HTTP request/response handlers
│   │   ├── __init__.py
│   │   ├── activity_controller.py
│   │   └── ...
│   │
│   ├── routes/          # API endpoints
│   │   ├── __init__.py
│   │   ├── activities_new.py
│   │   └── ...
│   │
│   ├── core/            # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   └── ...
│   │
│   └── middleware/      # Cross-cutting concerns
│       ├── __init__.py
│       └── ...
```

---

## 🎯 Implementation Example: Activity Module

### Complete Flow for Creating an Activity:

1. **Route** (`routes/activities_new.py`):
```python
@router.post("/")
async def create_activity(activity_data: ActivityCreate, ...):
    controller = ActivityController(db)
    return await controller.create_activity(activity_data, current_user)
```

2. **Controller** (`controllers/activity_controller.py`):
```python
async def create_activity(self, activity_data, current_user):
    # Check permissions
    if not self._check_create_permission(current_user):
        raise HTTPException(403)
    
    # Delegate to service
    return self.service.create_activity(activity_data, current_user)
```

3. **Service** (`services/activity_service.py`):
```python
def create_activity(self, activity_data, current_user):
    # Business logic
    activity_dict = activity_data.dict(exclude={'custom_fields'})
    activity_dict['user_id'] = current_user.id
    
    # Use repository
    db_activity = self.repository.create(obj_in=activity_dict)
    
    # Orchestrate with other services
    CustomFieldService.save_custom_field_values(...)
    
    self.db.commit()
    return self._build_response(db_activity)
```

4. **Repository** (`repositories/activity_repository.py`):
```python
def create(self, obj_in: Dict) -> Activity:
    db_obj = Activity(**obj_in)
    self.db.add(db_obj)
    self.db.flush()
    return db_obj
```

---

## ✅ Benefits of This Architecture

1. **Separation of Concerns**: Each layer has a single, clear responsibility
2. **Testability**: Easy to unit test each layer independently
3. **Maintainability**: Changes in one layer don't affect others
4. **Scalability**: Easy to add new features following the same pattern
5. **Reusability**: Services and repositories can be reused across different endpoints
6. **Clarity**: New developers can easily understand the codebase structure
7. **Best Practices**: Follows industry-standard patterns (Repository, Service, Controller)

---

## 🚀 Next Steps

After implementing Activity module as reference:

1. Migrate other modules (Contacts, Companies, Deals, etc.) to this structure
2. Add comprehensive error handling middleware
3. Implement request logging middleware
4. Add rate limiting middleware
5. Create integration tests for each layer
6. Add API versioning support

---

## 📚 Reference Implementation

The **Activity** module serves as the reference implementation for this architecture:

- ✅ `models/activity.py` - Database model
- ✅ `schemas/activity.py` - Request/response schemas
- ✅ `repositories/activity_repository.py` - Data access
- ✅ `services/activity_service.py` - Business logic
- ✅ `controllers/activity_controller.py` - HTTP handling
- ✅ `routes/activities_new.py` - API endpoints

Use this as a template for migrating other modules!
