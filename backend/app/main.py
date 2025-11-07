from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from .core.database import engine, Base
from .routes import auth, contacts_new, tasks_new, dashboard, users_new, roles_new, system_config_new, custom_fields_new, email_templates_new, integrations_new, notes_new, activities_new, companies_new, deals_new, storage, campaigns, prospects
# Import all models to ensure SQLAlchemy relationships are set up properly
from . import models
import traceback
import os
from pathlib import Path

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CRM API", version="1.0.0")

# Add request logging middleware for debugging


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Incoming request - {request.method} {request.url}")
    print(f"DEBUG: Headers: {dict(request.headers)}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response

# CORS middleware - MUST be added BEFORE routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
# New modular architecture (world-class production-level)
app.include_router(contacts_new.router,
                   prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(activities_new.router,
                   prefix="/api/v1/activities", tags=["activities"])
app.include_router(companies_new.router,
                   prefix="/api/v1/companies", tags=["companies"])
app.include_router(deals_new.router, prefix="/api/v1/deals", tags=["deals"])
app.include_router(tasks_new.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(
    dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(users_new.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles_new.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(system_config_new.router,
                   prefix="/api/v1", tags=["system-config"])
app.include_router(custom_fields_new.router,
                   prefix="/api/v1", tags=["custom-fields"])
app.include_router(email_templates_new.router,
                   prefix="/api/v1/email-templates", tags=["email-templates"])
app.include_router(integrations_new.router,
                   prefix="/api/v1/integrations", tags=["integrations"])
app.include_router(notes_new.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(storage.router, prefix="/api/v1/storage", tags=["storage"])
app.include_router(
    campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(
    prospects.router, prefix="/api/v1/prospects", tags=["prospects"])

# Global exception handler to preserve CORS headers


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and ensure CORS headers are present"""
    error_detail = str(exc)
    print(f"Unhandled exception: {error_detail}")
    print(traceback.format_exc())

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": error_detail,
            "type": "internal_server_error"
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with CORS headers"""
    # Decode body if it's bytes
    body = exc.body
    if isinstance(body, bytes):
        try:
            body = body.decode('utf-8')
        except Exception:
            body = str(body)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )




@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Mount static files for React frontend (if dist folder exists)
frontend_dist_path = Path(__file__).parent / "dist"
if frontend_dist_path.exists():
    # Mount static files (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="assets")
    
    # Catch-all route to serve index.html for client-side routing
    # This MUST be last to not interfere with API routes
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        
        # Serve index.html for all other routes (React Router will handle)
        index_file = frontend_dist_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})

