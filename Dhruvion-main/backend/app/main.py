from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import register_exception_handlers
from app.api.routes import router
from app.api.routes_v2 import router as routes_v2_router
from app.api.auth import router as auth_router
from app.core.database import Base, engine
from app.core import models  # noqa: F401

# Setup logging first
setup_logging()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Static files for processed data
static_dir = settings.PROCESSED_DIR
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers with API version prefix
app.include_router(router, prefix=settings.API_PREFIX)
app.include_router(routes_v2_router, prefix=settings.API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)

# Create database tables
Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return JSONResponse(
        content={
            "name": settings.API_TITLE,
            "version": settings.API_VERSION,
            "description": "DHRUVION Martian Mission Intelligence API",
            "docs_url": "/docs",
            "health_endpoint": "/health",
            "api_prefix": settings.API_PREFIX,
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint - independent of external services."""
    return JSONResponse(
        content={
            "status": "ok",
            "service": "dhruvion-api",
            "version": settings.API_VERSION,
        }
    )