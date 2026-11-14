from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.api.auth import router as auth_router
from app.core.database import Base, engine
from app.core import models  # noqa: F401

app = FastAPI(title="DHRUVION API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")

Base.metadata.create_all(bind=engine)
