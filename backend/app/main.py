from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from .core.database import engine, Base
from .routes import auth, contacts_new, tasks_new, dashboard, users_new, roles_new, system_config_new, custom_fields_new, email_templates_new, integrations_new, notes_new, activities_new, companies_new, deals_new, storage, campaigns, prospects, calendar_integration
# Import all models to ensure SQLAlchemy relationships are set up properly
from . import models
import traceback
import os
from pathlib import Path

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CRM API", version="1.0.0")

# CORS middleware - MUST be added BEFORE routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Health check route BEFORE routers
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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
app.include_router(calendar_integration.router,
                   prefix="/api/v1/calendar-integration", tags=["calendar-integration"])
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


# Mount static files for React frontend (if dist folder exists)
# IMPORTANT: This MUST be at the end, after all API routes are registered
frontend_dist_path = Path(__file__).parent / "dist"
if frontend_dist_path.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="assets")
    
    # Custom 404 handler to serve React app for non-API routes
    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc):
        # If it's an API route, return JSON 404
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        
        # For non-API routes, serve the React app (SPA)
        index_file = frontend_dist_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        
        return JSONResponse(status_code=404, content={"detail": "Page not found"})

