from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import register_exception_handlers
from app.api.routes import router
from app.api.routes_assistant import router as routes_assistant_router
from app.api.routes_missions import router as routes_missions_router
from app.api.routes_environment import router as routes_environment_router
from app.api.routes_planning import router as routes_planning_router
from app.api.routes_v2 import router as routes_v2_router
from app.api.auth import router as auth_router
from app.core.database import Base, engine
from app.core import models  # noqa: F401
from app.core.models import User
from app.core.security import hash_password
from app.data_pipeline.dataset_paths import get_dataset_paths

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
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Static files for processed data. The NASA handover package is mounted under a
# dedicated prefix so package-relative URLs never depend on a developer path.
# Mount the more specific prefix first: Starlette resolves mounts in order.
dataset_paths = get_dataset_paths()
if dataset_paths is not None and dataset_paths.processed_dir.is_dir():
    app.mount(
        settings.DATASET_STATIC_MOUNT,
        StaticFiles(directory=str(dataset_paths.processed_dir)),
        name="dhruvion-dataset",
    )

static_dir = settings.PROCESSED_DIR
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers with API version prefix
app.include_router(router, prefix=settings.API_PREFIX)
app.include_router(routes_planning_router, prefix=settings.API_PREFIX)
app.include_router(routes_environment_router, prefix=settings.API_PREFIX)
app.include_router(routes_v2_router, prefix=settings.API_PREFIX)
app.include_router(routes_assistant_router, prefix=settings.API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(routes_missions_router, prefix=settings.API_PREFIX)

# Create database tables
Base.metadata.create_all(bind=engine)


def _seed_demo_user() -> None:
    """Seed demo user idempotently on startup."""
    DEMO_EMAIL = "demo@dhruvion.io"
    DEMO_PASSWORD = "Mission2026!"
    DEMO_NAME = "Demo Operator"
    
    with Session(engine) as db:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            return
        password_hash = hash_password(DEMO_PASSWORD)
        demo_user = User(
            email=DEMO_EMAIL,
            full_name=DEMO_NAME,
            password_hash=password_hash,
            is_active=True,
        )
        db.add(demo_user)
        db.commit()


# Seed demo user on startup (idempotent)
@app.on_event("startup")
async def seed_demo_user_on_startup():
    _seed_demo_user()


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