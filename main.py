from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from core.database import engine, Base
from routes import auth, contacts_new, tasks_new, dashboard, users_new, roles_new, system_config_new, custom_fields_new, email_templates_new, integrations_new, notes_new, activities_new, companies_new, deals_new, storage, campaigns, prospects
# Import all models to ensure SQLAlchemy relationships are set up properly
import models
import traceback

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
        except:
            body = str(body)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )


# Define the path to your React build directory
FRONTEND_DIR = Path(__file__) / "dist"

# Check if frontend directory exists
if FRONTEND_DIR.exists():
    # Mount static files for React app assets - this handles /assets/* automatically
    app.mount(
        "/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    # Root route to serve React app
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        """Serve the React app at root"""
        index_file = FRONTEND_DIR / "index.html"
        try:
            # Read the HTML content and return as HTMLResponse
            html_content = index_file.read_text(encoding='utf-8')
            return HTMLResponse(
                content=html_content,
                status_code=200,
                headers={"Content-Type": "text/html; charset=utf-8"}
            )
        except Exception as e:
            print(f"Error reading index.html: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Error serving frontend"}
            )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        """
        Handle 404 errors by serving the React app for non-API routes.
        API routes will still return proper 404 JSON responses.
        """
        path = request.url.path

        # Return JSON 404 for API routes
        if path.startswith("/api/") or path in ["/docs", "/redoc", "/openapi.json"]:
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"}
            )

        # Serve React app for all other routes (client-side routing)
        if FRONTEND_DIR.exists():
            index_file = FRONTEND_DIR / "index.html"
            if index_file.exists():
                try:
                    # Read the HTML content and return as HTMLResponse
                    html_content = index_file.read_text(encoding='utf-8')
                    return HTMLResponse(
                        content=html_content,
                        status_code=200,
                        headers={"Content-Type": "text/html; charset=utf-8"}
                    )
                except Exception as e:
                    print(f"Error reading index.html: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={"detail": "Error serving frontend"}
                    )

        # Fallback JSON response if frontend not available
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
else:
    print("Warning: Frontend directory not found. Frontend serving disabled.")

    @app.get("/")
    async def read_root():
        return {"message": "API is running. Frontend not found - build your React app first."}

# @app.get("/")
# async def root():
#     return {"message": "CRM API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
